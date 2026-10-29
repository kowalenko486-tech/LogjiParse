import json
from unittest.mock import patch, MagicMock
from uuid import UUID
from app.models import LogisticQuery, UserSubscription

# UUID testowe (zgodne z mockiem)
TEST_USER_ID = "98bc203e-d9a2-4a0b-90f7-111fbfa251bd"

def test_incoming_mail_webhook_success(client, db_session):
    # Tworzymy profil użytkownika w bazie testowej, aby powiązać maila
    user_sub = UserSubscription(id=UUID(TEST_USER_ID), email="test@lojiparse.com", subscription_status="active")
    db_session.add(user_sub)
    db_session.commit()

    # Przykładowy payload z Mailgun dla inbound mail
    # Dopasowujemy recipient tak, by zawierał UUID użytkownika w To
    payload = {
        "sender": "cargo-owner@example.com",
        "recipient": f"inbound-{TEST_USER_ID}@inbound.lojiparse.com",
        "subject": "Zapytanie transportowe",
        "body-plain": "Wycena trasy Wrocław - Kraków dla 2 palet.",
        "timestamp": "1700000000",
        "token": "test-token",
        "signature": "test-signature"
    }

    # Patchujemy funkcję weryfikującą podpis Mailgun, by zawsze zwracała True w testach
    with patch("app.routers.webhook.verify_mailgun_signature", return_value=True):
        # Patchujemy również zadanie w tle, by nie odpytywać API OpenAI
        with patch("app.routers.webhook.process_email_in_background") as mock_background_task:
            response = client.post(
                "/api/v1/webhook/incoming-mail",
                json=payload
            )
            
            # Sprawdzenie statusu odpowiedzi API
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            
            # Weryfikacja zapisu w bazie danych
            saved_query = db_session.query(LogisticQuery).filter(LogisticQuery.sender == "cargo-owner@example.com").first()
            assert saved_query is not None
            assert saved_query.user_id == UUID(TEST_USER_ID)
            assert saved_query.status == "received"
            
            # Weryfikacja czy zadanie w tle zostało zaplanowane
            mock_background_task.assert_called_once()

def test_stripe_webhook_checkout_completed(client, db_session):
    # Inicjujemy pusty profil użytkownika bez subskrypcji
    user_id = UUID(TEST_USER_ID)
    user_sub = UserSubscription(id=user_id, email="client@firma.pl", subscription_status="inactive")
    db_session.add(user_sub)
    db_session.commit()

    # Payload zdarzenia Stripe: checkout.session.completed
    stripe_event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "client_reference_id": TEST_USER_ID,
                "customer": "cus_12345",
                "subscription": "sub_12345",
                "customer_details": {
                    "email": "client@firma.pl"
                }
            }
        }
    }

    # Mockujemy weryfikację webhooka Stripe
    with patch("app.routers.webhook.verify_stripe_webhook", return_value=stripe_event):
        response = client.post(
            "/api/v1/webhook/stripe",
            json=stripe_event,
            headers={"Stripe-Signature": "test-sig"}
        )
        
        assert response.status_code == 200
        
        # Sprawdzamy czy zaktualizowano bazę danych
        db_session.refresh(user_sub)
        assert user_sub.stripe_customer_id == "cus_12345"
        assert user_sub.stripe_subscription_id == "sub_12345"
        assert user_sub.subscription_status == "active"

def test_stripe_webhook_subscription_deleted(client, db_session):
    # Tworzymy aktywną subskrypcję w bazie
    user_id = UUID(TEST_USER_ID)
    user_sub = UserSubscription(
        id=user_id, 
        email="client@firma.pl", 
        stripe_customer_id="cus_12345",
        stripe_subscription_id="sub_12345",
        subscription_status="active"
    )
    db_session.add(user_sub)
    db_session.commit()

    # Payload zdarzenia Stripe: customer.subscription.deleted
    stripe_event = {
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "customer": "cus_12345",
                "id": "sub_12345",
                "status": "canceled"
            }
        }
    }

    with patch("app.routers.webhook.verify_stripe_webhook", return_value=stripe_event):
        response = client.post(
            "/api/v1/webhook/stripe",
            json=stripe_event,
            headers={"Stripe-Signature": "test-sig"}
        )
        
        assert response.status_code == 200
        
        # Sprawdzamy czy anulowano subskrypcję w bazie
        db_session.refresh(user_sub)
        assert user_sub.subscription_status == "inactive"
