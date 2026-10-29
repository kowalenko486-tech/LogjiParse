from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

# --- Schematy do walidacji danych bazy danych ---

class UserSubscriptionBase(BaseModel):
    email: EmailStr

class UserSubscriptionCreate(UserSubscriptionBase):
    id: UUID

class UserSubscriptionRead(UserSubscriptionBase):
    id: UUID
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    subscription_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class LogisticQueryRead(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    sender: str
    recipient: str
    subject: Optional[str] = None
    body: str
    parsed_data: Optional[Dict[str, Any]] = None
    status: str
    quote_price: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Schemat dla OpenAI Structured Outputs (Logistyka) ---

class CargoItem(BaseModel):
    description: str = Field(description="Description of the goods (e.g. electronics, car parts, clothes)")
    pieces: Optional[int] = Field(None, description="Number of items or packages")
    weight_kg: Optional[float] = Field(None, description="Weight in kilograms")
    length_cm: Optional[float] = Field(None, description="Length in centimeters")
    width_cm: Optional[float] = Field(None, description="Width in centimeters")
    height_cm: Optional[float] = Field(None, description="Height in centimeters")

class LogisticCargoDetails(BaseModel):
    origin_city: str = Field(description="City and country or region where cargo is picked up")
    origin_postcode: Optional[str] = Field(None, description="Postal code of pickup location")
    destination_city: str = Field(description="City and country or region where cargo is delivered")
    destination_postcode: Optional[str] = Field(None, description="Postal code of delivery location")
    cargo_items: List[CargoItem] = Field(default_factory=list, description="List of items or packages to transport")
    total_weight_kg: Optional[float] = Field(None, description="Total weight of all cargo in kilograms")
    total_volume_cbm: Optional[float] = Field(None, description="Total volume of the cargo in cubic meters (CBM)")
    handling_instructions: Optional[str] = Field(None, description="Special instructions like temperature control, stackability, ADR/dangerous goods")
    estimated_distance_km: Optional[float] = Field(None, description="Rough estimate of transit distance in kilometers")
    suggested_price_eur: Optional[float] = Field(None, description="Suggested shipping quote in EUR based on cargo details, route and standard logistics rates")

# --- Schematy dla webhooków ---

class MailgunWebhookPayload(BaseModel):
    sender: str = Field(..., alias="sender", description="Sender's email address")
    recipient: str = Field(..., alias="recipient", description="Recipient's email address (TO field)")
    subject: Optional[str] = Field("", alias="subject", description="Email subject")
    body_plain: str = Field(..., alias="body-plain", description="Plain text email body")
    
    # Do weryfikacji sygnatury Mailgun
    timestamp: str
    token: str
    signature: str

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
