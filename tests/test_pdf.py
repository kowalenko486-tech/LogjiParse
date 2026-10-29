import io
from datetime import datetime, timezone
from app.services.pdf_generator import generate_quotation_pdf

def test_generate_quotation_pdf():
    # Przygotowanie mockowych danych wejściowych
    parsed_data = {
        "origin_city": "Kraków, PL",
        "origin_postcode": "30-001",
        "destination_city": "Paris, FR",
        "destination_postcode": "75001",
        "total_weight_kg": 850.0,
        "total_volume_cbm": 4.5,
        "handling_instructions": "ADR class 9, keep dry",
        "estimated_distance_km": 1450.0,
        "cargo_items": [
            {
                "description": "Bębny kablowe",
                "pieces": 2,
                "weight_kg": 425.0,
                "length_cm": 120.0,
                "width_cm": 120.0,
                "height_cm": 100.0
            }
        ]
    }
    
    # Generowanie PDF
    pdf_buffer = generate_quotation_pdf(
        query_id="TEST-123",
        sender_email="spedytor@firma.pl",
        recipient_email="inbound-user@lojiparse.com",
        parsed_data=parsed_data,
        price=1850.0,
        created_at=datetime.now(timezone.utc)
    )
    
    # Sprawdzenie poprawności bufora
    assert isinstance(pdf_buffer, io.BytesIO)
    pdf_bytes = pdf_buffer.getvalue()
    
    # Sprawdzenie nagłówka pliku PDF (%PDF-...)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000  # Powinien mieć co najmniej 1KB
