import re
import hmac
import hashlib
import logging
import json
from fastapi import APIRouter, Request, Depends, HTTPException, status, BackgroundTasks, Header
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.database import get_db
from app.models import LogisticQuery, UserSubscription
from app.schemas import MailgunWebhookPayload
from app.services.openai_parser import parse_logistic_email
from app.services.stripe_service import verify_stripe_webhook
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/webhook", tags=["webhooks"])

# Wyrażenie regularne do wyciągania UUID z adresu email odbiorcy
UUID_REGEX = re.compile(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', re.I)

def verify_mailgun_signature(signing_key: str, timestamp: str, token: str, signature: str) -> bool:
    """
    Weryfikuje podpis webhooka z Mailgun za pomocą klucza podpisu (Signing Key).
    """
    if not signing_key or signing_key.startswith("your-"):
        logger.warning("Mailgun signing key is not set. Skipping signature validation.")
        return True
    
    hmac_digest = hmac.new(
        key=signing_key.encode('utf-8'),
        msg=f"{timestamp}{token}".encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(hmac_digest, signature)

def extract_user_id_from_email(recipient: str) -> Optional[UUID]:
    """
    Wyodrębnia UUID użytkownika z pola adresata (To/Recipient).
    NP: mail-98bc203e-d9a2-4a0b-90f7-111fbfa251bd@inbound.lojiparse.com -> UUID
    """
    match = UUID_REGEX.search(recipient)
    if match:
        try:
            return UUID(match.group(0))
        except ValueError:
            return None
    return None

def process_email_in_background(query_id: UUID, db_session_factory):
    """
    Zadanie działające w tle: pobiera mail z bazy danych, wysyła go do OpenAI
    w celu sparsowania, a następnie aktualizuje status i kwotę wyceny.
    """
    db = db_session_factory()
    try:
        # Pobranie zapytania
        query = db.query(LogisticQuery).filter(LogisticQuery.id == query_id).first()
        if not query:
            logger.error(f"Background task: Query {query_id} not found in database.")
            return

        query.status = "parsing"
        db.commit()

        # Przekazanie do parsera OpenAI (gpt-4o-mini)
        logger.info(f"Background task: Parsing email {query_id} with OpenAI...")
        parsed_data = parse_logistic_email(query.body, query.subject or "")
        
        # Zapisanie wyników w bazie danych
        query.parsed_data = parsed_data.model_dump()
        query.quote_price = parsed_data.suggested_price_eur
        query.status = "parsed"
        db.commit()
        logger.info(f"Background task: Successfully parsed email {query_id}.")
        
    except Exception as e:
        logger.error(f"Background task: Failed to parse email {query_id}: {str(e)}")
        # Próba oznaczenia rekordu jako błędu w bazie danych
        try:
            query = db.query(LogisticQuery).filter(LogisticQuery.id == query_id).first()
            if query:
                query.status = "failed"
                db.commit()
        except Exception as db_err:
            logger.error(f"Database error during fail-state commit: {str(db_err)}")
    finally:
        db.close()

@router.post("/incoming-mail")
async def incoming_mail_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Endpoint webhooka Mailgun /api/v1/webhook/incoming-mail
    Może przyjmować JSON lub standardowy x-www-form-urlencoded z Mailgun.
    """
    content_type = request.headers.get("content-type", "")
    
    # Obsługa zarówno JSON, jak i form-data z Mailgun Inbound
    if "application/json" in content_type:
        payload_data = await request.json()
        sender = payload_data.get("sender")
        recipient = payload_data.get("recipient")
        subject = payload_data.get("subject", "")
        body_plain = payload_data.get("body-plain")
        
        # Dane do podpisu
        timestamp = payload_data.get("timestamp")
        token = payload_data.get("token")
        signature = payload_data.get("signature")
    else:
        # Mailgun domyślnie wysyła multipart/form-data lub application/x-www-form-urlencoded
        form_data = await request.form()
        sender = form_data.get("sender")
        recipient = form_data.get("recipient")
        subject = form_data.get("subject", "")
        body_plain = form_data.get("body-plain")
        
        # Dane do podpisu
        timestamp = form_data.get("timestamp")
        token = form_data.get("token")
        signature = form_data.get("signature")

    # Walidacja pól wymaganych
    if not sender or not recipient or not body_plain:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Brak wymaganych pól maila (sender, recipient, body-plain)."
        )

    # Weryfikacja sygnatury Mailgun
    if timestamp and token and signature:
        if not verify_mailgun_signature(settings.MAILGUN_SIGNING_KEY, timestamp, token, signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Błąd autoryzacji Mailgun (nieprawidłowa sygnatura)."
            )

    # Wyciągnięcie UUID użytkownika z pola adresata
    user_id = extract_user_id_from_email(recipient)
    
    # Zapewnienie, że rekord użytkownika istnieje w bazie (zapobiega naruszeniu klucza obcego)
    if user_id:
        user_exists = db.query(UserSubscription).filter(UserSubscription.id == user_id).first()
        if not user_exists:
            user_exists = UserSubscription(
                id=user_id,
                email=f"inbound-{user_id}@lojiparse.com",
                subscription_status="active"
            )
            db.add(user_exists)
            db.commit()
            logger.info(f"Auto-created user subscription profile for ID {user_id} to prevent FK violation.")
    else:
        logger.warning(f"Could not extract user_id from recipient field: {recipient}")

    # Utworzenie nowego zapytania w bazie
    db_query = LogisticQuery(
        user_id=user_id,
        sender=sender,
        recipient=recipient,
        subject=subject,
        body=body_plain,
        status="received"
    )
    db.add(db_query)
    db.commit()
    db.refresh(db_query)
    
    # Uruchomienie parsowania w tle
    # Przekazujemy fabrykę sesji, by zadanie w tle miało własną niezależną sesję DB
    from app.database import SessionLocal
    background_tasks.add_task(process_email_in_background, db_query.id, SessionLocal)
    
    return {
        "status": "success", 
        "message": "Email received and queued for processing.",
        "query_id": str(db_query.id)
    }

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db)
):
    """
    Endpoint webhooka dla Stripe: synchronizuje statusy subskrypcji w tabeli user_subscriptions.
    """
    payload = await request.body()
    
    try:
        event = verify_stripe_webhook(payload, stripe_signature)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Stripe Signature: {str(e)}"
        )
        
    event_type = event.get("type")
    data_object = event.get("data", {}).get("object", {})
    
    logger.info(f"Received Stripe webhook event: {event_type}")
    
    if event_type == "checkout.session.completed":
        # Klient ukończył transakcję. Pobieramy client_reference_id (UUID użytkownika)
        user_id_str = data_object.get("client_reference_id")
        customer_id = data_object.get("customer")
        subscription_id = data_object.get("subscription")
        
        # Pobieramy email klienta jeśli podany
        customer_details = data_object.get("customer_details", {})
        email = customer_details.get("email") or "unknown@lojiparse.com"
        
        if user_id_str:
            try:
                user_id = UUID(user_id_str)
                # Szukamy użytkownika w user_subscriptions
                user_sub = db.query(UserSubscription).filter(UserSubscription.id == user_id).first()
                if not user_sub:
                    # Tworzymy nowy rekord subskrypcji jeśli nie istnieje
                    user_sub = UserSubscription(id=user_id, email=email)
                    db.add(user_sub)
                    
                user_sub.stripe_customer_id = customer_id
                user_sub.stripe_subscription_id = subscription_id
                user_sub.subscription_status = "active"
                db.commit()
                logger.info(f"Subscription activated for user {user_id} via Stripe Checkout completed.")
            except ValueError:
                logger.error(f"Invalid UUID client_reference_id: {user_id_str}")
        else:
            logger.error("No client_reference_id provided in checkout session. Attempting email fallback.")
            if email:
                user_sub = db.query(UserSubscription).filter(UserSubscription.email == email).first()
                if user_sub:
                    user_sub.stripe_customer_id = customer_id
                    user_sub.stripe_subscription_id = subscription_id
                    user_sub.subscription_status = "active"
                    db.commit()
                    logger.info(f"Subscription activated for user {user_sub.id} via Stripe email fallback ({email}).")
                else:
                    logger.error(f"No user subscription found matching email: {email}")
            else:
                logger.error("No email available for Stripe fallback matching.")
            
    elif event_type in ["customer.subscription.updated", "customer.subscription.deleted"]:
        subscription_id = data_object.get("id")
        customer_id = data_object.get("customer")
        status = data_object.get("status")
        
        # Szukamy subskrypcji po stripe_subscription_id lub stripe_customer_id
        user_sub = db.query(UserSubscription).filter(
            (UserSubscription.stripe_subscription_id == subscription_id) | 
            (UserSubscription.stripe_customer_id == customer_id)
        ).first()
        
        if user_sub:
            if event_type == "customer.subscription.deleted" or status in ["canceled", "unpaid"]:
                user_sub.subscription_status = "inactive"
            else:
                user_sub.subscription_status = status  # active, trialing, past_due, itp.
                
            db.commit()
            logger.info(f"Updated subscription status to '{user_sub.subscription_status}' for user {user_sub.id}.")
        else:
            logger.warning(f"No user subscription found matching subscription_id {subscription_id} or customer_id {customer_id}")
            
    return {"status": "success"}

@router.post("/lemonsqueezy")
async def lemonsqueezy_webhook(
    request: Request,
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    db: Session = Depends(get_db)
):
    """
    Endpoint webhooka dla Lemon Squeezy: synchronizuje statusy subskrypcji
    w tabeli user_subscriptions na podstawie zdarzeń z platformy Lemon Squeezy.
    """
    payload = await request.body()
    
    # Weryfikacja sygnatury Lemon Squeezy
    if x_signature:
        if not verify_lemonsqueezy_signature(payload, x_signature, settings.LEMONSQUEEZY_WEBHOOK_SECRET):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Błąd autoryzacji Lemon Squeezy (nieprawidłowa sygnatura)."
            )
            
    try:
        event = json.loads(payload.decode('utf-8'))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Błędny format JSON: {str(e)}"
        )
        
    meta = event.get("meta", {})
    event_name = meta.get("event_name")
    custom_data = meta.get("custom_data", {})
    
    # Wyciągamy UUID użytkownika przekazany w linku checkoutu
    user_id_str = custom_data.get("user_id") if isinstance(custom_data, dict) else None
    
    data_object = event.get("data", {})
    attributes = data_object.get("attributes", {})
    status_str = attributes.get("status")
    email = attributes.get("user_email") or "unknown@lemonsqueezy.com"
    
    logger.info(f"Received Lemon Squeezy webhook event: {event_name}")
    
    # Interesują nas głównie zdarzenia dotyczące subskrypcji
    if event_name and event_name.startswith("subscription_"):
        if user_id_str:
            try:
                user_id = UUID(user_id_str)
                user_sub = db.query(UserSubscription).filter(UserSubscription.id == user_id).first()
                if not user_sub:
                    # Tworzymy rekord jeśli nie istnieje
                    user_sub = UserSubscription(id=user_id, email=email)
                    db.add(user_sub)
                
                # Zapisujemy ID subskrypcji i klienta z Lemon Squeezy
                user_sub.stripe_customer_id = f"ls_customer_{attributes.get('customer_id')}"
                user_sub.stripe_subscription_id = f"ls_sub_{data_object.get('id')}"
                
                # Aktualizacja statusu
                if event_name in ["subscription_cancelled", "subscription_expired"] or status_str in ["cancelled", "expired", "unpaid"]:
                    user_sub.subscription_status = "inactive"
                else:
                    user_sub.subscription_status = "active"
                    
                db.commit()
                logger.info(f"Lemon Squeezy subscription updated for user {user_id}: {user_sub.subscription_status}")
            except ValueError:
                logger.error(f"Invalid UUID in Lemon Squeezy custom_data: {user_id_str}")
        else:
            logger.error("No user_id provided in Lemon Squeezy webhook custom_data. Attempting email fallback.")
            if email:
                user_sub = db.query(UserSubscription).filter(UserSubscription.email == email).first()
                if user_sub:
                    user_sub.stripe_customer_id = f"ls_customer_{attributes.get('customer_id')}"
                    user_sub.stripe_subscription_id = f"ls_sub_{data_object.get('id')}"
                    
                    if event_name in ["subscription_cancelled", "subscription_expired"] or status_str in ["cancelled", "expired", "unpaid"]:
                        user_sub.subscription_status = "inactive"
                    else:
                        user_sub.subscription_status = "active"
                        
                    db.commit()
                    logger.info(f"Lemon Squeezy subscription updated for user {user_sub.id} via email fallback ({email}).")
                else:
                    logger.error(f"No user subscription found matching email: {email}")
            else:
                logger.error("No email available for Lemon Squeezy fallback matching.")
            
    return {"status": "success"}

def verify_lemonsqueezy_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Weryfikuje podpis webhooka z Lemon Squeezy.
    """
    if not secret or secret.startswith("your-"):
        logger.warning("Lemon Squeezy webhook secret is not set. Skipping signature validation.")
        return True
        
    local_signature = hmac.new(
        key=secret.encode('utf-8'),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(local_signature, signature)
