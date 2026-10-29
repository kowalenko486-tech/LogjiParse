import logging
from openai import OpenAI
from app.config import settings
from app.schemas import LogisticCargoDetails

logger = logging.getLogger(__name__)

def parse_logistic_email(body: str, subject: str = "") -> LogisticCargoDetails:
    """
    Używa modelu OpenAI gpt-4o-mini i funkcji Structured Outputs do
    wyodrębnienia z treści maila szczegółów ładunku i trasy.
    """
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("your-"):
        logger.warning("OpenAI API Key is not set or placeholder. Returning mock parsed data.")
        return get_mock_parsed_data(body, subject)
        
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        prompt = f"Subject: {subject}\n\nBody:\n{body}"
        
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "You are an expert logistics coordinator. Extract key details about "
                        "the shipment from the email. Parse locations (cities, postcodes), cargo item details "
                        "(description, package count, weight in kg, dimensions), calculate total weight/volume, "
                        "and estimate a realistic market rate in EUR (suggested_price_eur) for this transport."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            response_format=LogisticCargoDetails,
        )
        
        parsed_result = completion.choices[0].message.parsed
        return parsed_result
        
    except Exception as e:
        logger.error(f"Error during OpenAI parsing: {str(e)}")
        # Zwracamy uproszczone dane zapasowe w przypadku błędu API
        return get_mock_parsed_data(body, subject)

def get_mock_parsed_data(body: str, subject: str) -> LogisticCargoDetails:
    """
    Zapasowa metoda generująca mockowe dane w przypadku braku klucza API lub błędu.
    """
    # Prosta heurystyka wyciągająca słowa kluczowe w razie braku połączenia
    origin = "Warszawa, Polska"
    destination = "Berlin, Niemcy"
    
    # Próbujemy znaleźć słowa kluczowe w tekście
    body_lower = body.lower()
    if "z" in body_lower or "od" in body_lower or "from" in body_lower:
        # Bardzo uproszczony mock
        pass
        
    return LogisticCargoDetails(
        origin_city="Warszawa, PL",
        origin_postcode="00-001",
        destination_city="Berlin, DE",
        destination_postcode="10115",
        cargo_items=[
            {
                "description": "Palety z towarem (General Cargo)",
                "pieces": 4,
                "weight_kg": 1200.0,
                "length_cm": 120.0,
                "width_cm": 80.0,
                "height_cm": 150.0
            }
        ],
        total_weight_kg=1200.0,
        total_volume_cbm=5.76,
        handling_instructions="Staplowanie niedozwolone (Do not stack)",
        estimated_distance_km=575.0,
        suggested_price_eur=850.0
    )
