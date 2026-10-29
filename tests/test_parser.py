from unittest.mock import MagicMock, patch
from app.services.openai_parser import parse_logistic_email, get_mock_parsed_data
from app.schemas import LogisticCargoDetails

def test_get_mock_parsed_data():
    mock_data = get_mock_parsed_data("Test body", "Test subject")
    assert isinstance(mock_data, LogisticCargoDetails)
    assert mock_data.origin_city == "Warszawa, PL"
    assert mock_data.destination_city == "Berlin, DE"
    assert mock_data.suggested_price_eur == 850.0

@patch("app.services.openai_parser.OpenAI")
def test_parse_logistic_email_with_api_mock(mock_openai_class):
    # Skonfigurowanie mocka dla klienta OpenAI
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    
    # Symulujemy zwrotkę z API structured outputs
    mock_choice = MagicMock()
    mock_parsed_data = LogisticCargoDetails(
        origin_city="Poznań, PL",
        destination_city="Gdańsk, PL",
        total_weight_kg=500.0,
        cargo_items=[
            {
                "description": "Kartony z obuwiem",
                "pieces": 10,
                "weight_kg": 50.0
            }
        ],
        suggested_price_eur=400.0
    )
    mock_choice.message.parsed = mock_parsed_data
    mock_client.beta.chat.completions.parse.return_value.choices = [mock_choice]
    
    # Wywołanie z podmienionym kluczem, by nie wpadł w mock fallback
    with patch("app.config.settings.OPENAI_API_KEY", "real-api-key-value"):
        result = parse_logistic_email("Potrzebny transport z Poznania do Gdańska", "Fracht")
        
        # Weryfikacja
        assert result.origin_city == "Poznań, PL"
        assert result.destination_city == "Gdańsk, PL"
        assert result.suggested_price_eur == 400.0
        mock_client.beta.chat.completions.parse.assert_called_once()
