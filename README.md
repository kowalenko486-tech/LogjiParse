# LogjiParse 🚀
### AI-Powered Document & Logistics Parser Microservice

[![CI Tests](https://github.com/kowalenko486-tech/LogjiParse/actions/workflows/test.yml/badge.svg)](https://github.com/kowalenko486-tech/LogjiParse/actions)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-E92063?style=flat&logo=pydantic)](https://docs.pydantic.dev/)
[![OpenAI](https://img.shields.io/badge/OpenAI-Structured_Outputs-412991?style=flat&logo=openai)](https://platform.openai.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**LogjiParse** to produkcyjny mikroserwis w **Pythonie (FastAPI)** służący do automatycznej analizy, strukturyzacji i walidacji niestrukturyzowanych dokumentów biznesowych (zlecenia transportowe, specyfikacje ładunkowe, dokumenty CMR, faktury).

System eliminuje ręczne wprowadzanie danych poprzez połączenie modeli LLM z deterministyczną walidacją schematów **Pydantic v2** (*Zero-Hallucination Gate*), automatycznym generatorem dokumentów PDF (**ReportLab**) oraz integracją płatności (**Stripe**).

---

## 🏗️ Architektura Przepływu Danych

```text
  [ Niestrukturyzowany Dokument / E-mail / Tekst ]
                         │
                         ▼
           [ OpenAI Structured Outputs ]
         (Ekstrakcja parametrów do JSON)
                         │
                         ▼
              [ Pydantic v2 Gate ]
       (Rygorystyczna walidacja typów, sum,
         mas, wymiarów i reguł biznesowych)
                         │
                         ▼
             [ FastAPI Business Core ]
          ├── Zapis w PostgreSQL / Supabase
          ├── Generowanie ustrukturyzowanego PDF (ReportLab)
          └── Webhooki transakcyjne (Stripe / Lemon Squeezy)
```

---

## ✨ Kluczowe Funkcjonalności

* **Deterministyczne AI (Structured Outputs):** Wykorzystanie natywnego parsowania schematów Pydantic przez modele LLM (`client.beta.chat.completions.parse`), eliminujące błędy formatowania i niekompletne odpowiedzi.
* **Bramka Walidacji Pydantic v2:** Weryfikacja jednostek wagowych, współrzędnych tras, pozycji ładunkowych i kalkulacji cenowych przed jakimkolwiek zapisem do bazy.
* **Generator Dokumentów PDF:** Zautomatyzowane tworzenie estetycznych, gotowych do wydruku specyfikacji i raportów PDF w oparciu o bibliotekę **ReportLab** i fonty Unicode.
* **Bezpieczeństwo & Webhooki:** Weryfikacja podpisów kryptograficznych webhooków Stripe / Lemon Squeezy oraz autoryzacja zapytań przez tokeny Supabase JWT.
* **Gotowość do wdrożenia:** Przygotowana konfiguracja chmurowa pod Vercel (`vercel.json`) oraz Render (`render.yaml`).

---

## 🛠️ Stos Technologiczny

* **Język & Framework:** Python 3.12, FastAPI, Uvicorn
* **Walidacja danych:** Pydantic v2, Pydantic-Settings
* **Baza danych:** SQLAlchemy 2.0, PostgreSQL / Supabase
* **AI & LLM:** OpenAI API (GPT-4o / GPT-4o-mini z obsługą Structured Outputs)
* **Generowanie dokumentów:** ReportLab
* **Płatności:** Stripe API, Webhooks
* **Testy:** Pytest, HTTPX, Unittest Mock

---

## 🚀 Szybki Start

### 1. Klonowanie repozytorium
```bash
git clone https://github.com/kowalenko486-tech/LogjiParse.git
cd LogjiParse
```

### 2. Środowisko wirtualne i instalacja zależności
```bash
python -m venv .venv
source .venv/bin/activate  # Na Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Konfiguracja zmiennych środowiskowych
Utwórz plik `.env` na podstawie poniższych parametrów:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
OPENAI_API_KEY=sk-...
SUPABASE_JWT_SECRET=your-secret
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### 4. Uruchomienie serwera deweloperskiego
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Interaktywna dokumentacja Swagger UI dostępna pod adresem: `http://localhost:8000/docs`.

---

## 🧪 Testy Automatyczne

Repozytorium zawiera pełny zestaw testów jednostkowych i integracyjnych z zamockowanymi wywołaniami zewnętrznych API:
```bash
pytest -v
```

---

## 📄 Licencja

Projekt udostępniany na licencji MIT. Zobacz plik [LICENSE](LICENSE) po więcej szczegółów.
