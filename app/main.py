import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import engine, Base
from app.routers import webhook, queries

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Automatyczne tworzenie tabel w bazie danych Supabase/PostgreSQL przy starcie
try:
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing database tables: {str(e)}")

app = FastAPI(
    title="LojiParse API", 
    description="Backend serwisu do parsowania zapytań logistycznych LojiParse",
    version="1.0.0"
)

# Konfiguracja CORS (przydatne do lokalnego developmentu)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dołączenie routerów API
app.include_router(webhook.router)
app.include_router(queries.router)

@app.get("/api/v1/config")
async def get_public_config():
    """
    Zwraca konfigurację publiczną Supabase potrzebną dla frontendu.
    """
    return {
        "supabase_url": os.getenv("SUPABASE_URL", "https://your-supabase-project.supabase.co"),
        "supabase_anon_key": os.getenv("SUPABASE_ANON_KEY", "your-supabase-anon-key-here")
    }

# Utworzenie ścieżki do folderu static, jeśli nie istnieje
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

# Mountowanie katalogu plików statycznych pod ścieżką /static
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def serve_dashboard():
    """
    Serwowanie głównego pliku index.html pod adresem głównym serwera.
    Zapobiegamy cache'owaniu strony przez przeglądarkę, by zmiany kodu były od razu widoczne.
    """
    index_path = os.path.join(static_dir, "index.html")
    if not os.path.exists(index_path):
        # Fallback w przypadku braku pliku index.html
        return {"status": "running", "message": "LojiParse API is running. Please create static/index.html"}
    return FileResponse(
        index_path,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )
