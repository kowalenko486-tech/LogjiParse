import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/postgres",
        validation_alias="DATABASE_URL"
    )
    
    # Supabase authentication JWT secret
    SUPABASE_JWT_SECRET: str = Field(
        default="your-supabase-jwt-secret-here",
        validation_alias="SUPABASE_JWT_SECRET"
    )
    
    # OpenAI API Key
    OPENAI_API_KEY: str = Field(
        default="your-openai-key-here",
        validation_alias="OPENAI_API_KEY"
    )
    
    # Stripe settings
    STRIPE_SECRET_KEY: str = Field(
        default="your-stripe-secret-key-here",
        validation_alias="STRIPE_SECRET_KEY"
    )
    STRIPE_WEBHOOK_SECRET: str = Field(
        default="your-stripe-webhook-secret-here",
        validation_alias="STRIPE_WEBHOOK_SECRET"
    )
    STRIPE_PAYMENT_LINK: str = Field(
        default="https://buy.stripe.com/test_dummy_payment_link",
        validation_alias="STRIPE_PAYMENT_LINK"
    )
    LEMONSQUEEZY_WEBHOOK_SECRET: str = Field(
        default="your-lemonsqueezy-webhook-secret-here",
        validation_alias="LEMONSQUEEZY_WEBHOOK_SECRET"
    )
    
    # Mailgun settings
    MAILGUN_SIGNING_KEY: str = Field(
        default="your-mailgun-signing-key-here",
        validation_alias="MAILGUN_SIGNING_KEY"
    )
    
    # App Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Allow reading from a .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Instancja ustawień globalnych
settings = Settings()
