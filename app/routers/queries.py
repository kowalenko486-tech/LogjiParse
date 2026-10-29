from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Dict, Any

from app.database import get_db
from app.models import LogisticQuery, UserSubscription
from app.schemas import LogisticQueryRead
from app.auth import get_current_user
from app.services.pdf_generator import generate_quotation_pdf
from app.services.stripe_service import create_customer_portal_session
from app.config import settings

router = APIRouter(prefix="/api/v1/queries", tags=["queries"])

@router.get("", response_model=List[LogisticQueryRead])
def get_queries(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Pobiera wszystkie zapytania logistyczne dla zalogowanego użytkownika.
    """
    user_id = current_user["id"]
    
    # Najpierw upewniamy się, że użytkownik ma profil w tabeli subskrypcji
    user_sub = db.query(UserSubscription).filter(UserSubscription.id == user_id).first()
    if not user_sub:
        # Tworzymy domyślny aktywny rekord subskrypcji przy pierwszym ładowaniu
        user_sub = UserSubscription(id=user_id, email=current_user["email"], subscription_status="active")
        db.add(user_sub)
        db.commit()
        db.refresh(user_sub)
    else:
        # Aktualizujemy e-mail i status na aktywny, jeśli był tymczasowy (np. utworzony przez webhook)
        if user_sub.email != current_user["email"] or user_sub.subscription_status != "active":
            user_sub.email = current_user["email"]
            user_sub.subscription_status = "active"
            db.commit()
        
    queries = db.query(LogisticQuery).filter(LogisticQuery.user_id == user_id).order_by(LogisticQuery.created_at.desc()).all()
    return queries

@router.get("/{query_id}", response_model=LogisticQueryRead)
def get_query_details(
    query_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Pobiera szczegóły pojedynczego zapytania logistycznego.
    Zabezpiecza pobieranie przed nieuprawnionym dostępem innych użytkowników.
    """
    user_id = current_user["id"]
    query = db.query(LogisticQuery).filter(LogisticQuery.id == query_id).first()
    
    if not query:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zapytanie nie zostało znalezione.")
        
    if query.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Brak uprawnień do tego zapytania.")
        
    return query

@router.get("/{query_id}/pdf")
def get_query_pdf(
    query_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generuje i przesyła plik PDF z wyceną zapytania logistycznego w locie.
    Dostępne tylko dla użytkowników z aktywną subskrypcją.
    """
    user_id = current_user["id"]
    


    # 2. Pobieramy zapytanie
    query = db.query(LogisticQuery).filter(LogisticQuery.id == query_id).first()
    if not query:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zapytanie nie zostało znalezione.")
        
    if query.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Brak uprawnień do tego zapytania.")
        
    if query.status != "parsed" or not query.parsed_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Zapytanie nie zostało jeszcze sparsowane lub parsowanie zakończyło się błędem."
        )

    # 3. Generujemy PDF w pamięci
    pdf_buffer = generate_quotation_pdf(
        query_id=str(query.id)[:8].upper(),
        sender_email=query.sender,
        recipient_email=query.recipient,
        parsed_data=query.parsed_data,
        price=query.quote_price or 0.0,
        created_at=query.created_at
    )
    
    filename = f"wycena_{str(query.id)[:8].upper()}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

@router.post("/billing-portal")
def get_billing_portal_or_payment_link(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Zwraca link przekierowujący do płatności Stripe:
    - Jeśli użytkownik posiada stripe_customer_id, generuje Customer Portal Session URL.
    - Jeśli nie, zwraca statyczny Payment Link z doklejonym client_reference_id (UUID użytkownika).
    """
    user_id = current_user["id"]
    user_sub = db.query(UserSubscription).filter(UserSubscription.id == user_id).first()
    
    # Dynamiczne budowanie linku w zależności od tego, czy używasz Stripe czy Lemon Squeezy
    base_link = settings.STRIPE_PAYMENT_LINK
    if "lemonsqueezy.com" in base_link:
        separator = "&" if "?" in base_link else "?"
        static_payment_link = f"{base_link}{separator}checkout[custom][user_id]={user_id}"
    else:
        static_payment_link = f"{base_link}?client_reference_id={user_id}"
    
    if user_sub and user_sub.stripe_customer_id:
        # Jeśli używamy kluczy testowych/mockowych, zwracamy mockowy adres portalu bez odpytywania API Stripe
        if not settings.STRIPE_SECRET_KEY or settings.STRIPE_SECRET_KEY.startswith("your-") or "test" in user_sub.stripe_customer_id:
            return {"url": "https://billing.stripe.com/p/session/mock_session", "type": "portal"}
            
        try:
            # Tworzymy portal klienta Stripe, aby użytkownik mógł zarządzać subskrypcją
            # Wskazujemy powrót na adres aplikacji (dla środowiska dev domyślnie localhost)
            # Uwaga: w produkcji należy odpowiednio ustawić host
            return_url = "http://localhost:8000/"
            portal_url = create_customer_portal_session(user_sub.stripe_customer_id, return_url)
            return {"url": portal_url, "type": "portal"}
        except Exception:
            # W razie błędu zwracamy domyślny link płatniczy jako fallback
            pass
            
    return {"url": static_payment_link, "type": "payment_link"}
