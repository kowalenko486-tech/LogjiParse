import pytest
from uuid import UUID, uuid4
from app.models import LogisticQuery, UserSubscription

TEST_USER_ID = "98bc203e-d9a2-4a0b-90f7-111fbfa251bd"
MOCK_HEADERS = {"Authorization": "Bearer mock-jwt-token-active"}

def test_get_queries_unauthorized(client):
    # Bez nagłówka Authorization powróci 401
    response = client.get("/api/v1/queries")
    assert response.status_code == 401

def test_get_queries_success(client, db_session):
    # Tworzymy profil i przykładowe zapytanie
    user_id = UUID(TEST_USER_ID)
    user_sub = UserSubscription(id=user_id, email="mock-user@lojiparse.com", subscription_status="active")
    query = LogisticQuery(
        user_id=user_id,
        sender="sender@example.com",
        recipient="inbound@lojiparse.com",
        subject="Test subject",
        body="Cargo info details...",
        status="parsed"
    )
    db_session.add(user_sub)
    db_session.add(query)
    db_session.commit()

    response = client.get("/api/v1/queries", headers=MOCK_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["sender"] == "sender@example.com"
    assert data[0]["subject"] == "Test subject"

def test_get_pdf_success_for_inactive_user(client, db_session):
    # Tworzymy profil o statusie inactive
    user_id = UUID(TEST_USER_ID)
    user_sub = UserSubscription(id=user_id, email="mock-user@lojiparse.com", subscription_status="inactive")
    query = LogisticQuery(
        id=uuid4(),
        user_id=user_id,
        sender="sender@example.com",
        recipient="inbound@lojiparse.com",
        subject="Test subject",
        body="Cargo details...",
        status="parsed",
        parsed_data={"origin_city": "Warszawa", "destination_city": "Berlin"},
        quote_price=500.0
    )
    db_session.add(user_sub)
    db_session.add(query)
    db_session.commit()

    # Nawet z inactive subskrypcją powinniśmy dostać 200 i plik PDF
    response = client.get(f"/api/v1/queries/{query.id}/pdf", headers=MOCK_HEADERS)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")

def test_get_pdf_success(client, db_session):
    # Tworzymy profil o statusie active
    user_id = UUID(TEST_USER_ID)
    user_sub = UserSubscription(id=user_id, email="mock-user@lojiparse.com", subscription_status="active")
    query = LogisticQuery(
        id=uuid4(),
        user_id=user_id,
        sender="sender@example.com",
        recipient="inbound@lojiparse.com",
        subject="Test subject",
        body="Cargo details...",
        status="parsed",
        parsed_data={"origin_city": "Warszawa", "destination_city": "Berlin"},
        quote_price=500.0
    )
    db_session.add(user_sub)
    db_session.add(query)
    db_session.commit()

    # Powinno zakończyć się sukcesem i zwrócić PDF
    response = client.get(f"/api/v1/queries/{query.id}/pdf", headers=MOCK_HEADERS)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
