import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Float, Text, func, Uuid
from app.database import Base

class UserSubscription(Base):
    """
    Tabela przechowująca status subskrypcji użytkownika, synchronizowana ze Stripe.
    Klucz główny 'id' odpowiada UUID użytkownika z Supabase Auth.
    """
    __tablename__ = "user_subscriptions"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, index=True)
    stripe_customer_id = Column(String, unique=True, nullable=True)
    stripe_subscription_id = Column(String, unique=True, nullable=True)
    subscription_status = Column(String, default="inactive", nullable=False) # e.g. active, inactive, trialing, past_due
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class LogisticQuery(Base):
    """
    Tabela przechowująca zapytania logistyczne z maili.
    """
    __tablename__ = "logistic_queries"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("user_subscriptions.id", ondelete="CASCADE"), nullable=True, index=True)
    sender = Column(String, nullable=False)
    recipient = Column(String, nullable=False)
    subject = Column(String, nullable=True)
    body = Column(Text, nullable=False)
    parsed_data = Column(JSON, nullable=True) # Przechowuje JSON wyodrębniony przez OpenAI
    status = Column(String, default="received", nullable=False) # received, parsing, parsed, failed
    quote_price = Column(Float, nullable=True) # Wyliczona cena
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
