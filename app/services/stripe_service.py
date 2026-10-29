import stripe
import logging
from app.config import settings

logger = logging.getLogger(__name__)

# Ustawienie klucza Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

def verify_stripe_webhook(payload: bytes, sig_header: str) -> dict:
    """
    Weryfikuje podpis webhooka Stripe i zwraca zdekodowany obiekt zdarzenia (Event).
    Zwraca None, jeśli weryfikacja się nie powiedzie.
    """
    if not settings.STRIPE_WEBHOOK_SECRET or settings.STRIPE_WEBHOOK_SECRET.startswith("your-"):
        logger.warning("Stripe Webhook Secret is not set. Skipping verification (unsafe, for testing only).")
        # W środowisku testowym bez sygnatury dekodujemy bezpośrednio payload
        import json
        return json.loads(payload)
        
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        return event
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Stripe Webhook Signature Verification Failed: {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"Stripe Webhook payload parsing error: {str(e)}")
        raise e

def create_customer_portal_session(customer_id: str, return_url: str) -> str:
    """
    Tworzy sesję portalu klienta Stripe (Stripe Billing Portal Session),
    umożliwiając zalogowanemu użytkownikowi zarządzanie subskrypcją (anulowanie, zmiana karty płatniczej).
    """
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return session.url
    except Exception as e:
        logger.error(f"Failed to create Stripe billing portal session: {str(e)}")
        raise e
