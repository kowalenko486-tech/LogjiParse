import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

logger = logging.getLogger(__name__)

# Pobieramy URL bazy danych
db_url = settings.DATABASE_URL

# Automatyczny fallback do lokalnego SQLite, jeśli URL wskazuje na domyślny localhost
# lub gdy brakuje konfiguracji zewnętrznej bazy Supabase
if "localhost:5432" in db_url or db_url == "postgresql://postgres:postgres@localhost:5432/postgres":
    if os.environ.get("VERCEL"):
        import tempfile
        db_path = os.path.join(tempfile.gettempdir(), "lojiparse.db")
        logger.warning(f"Środowisko Vercel wykryte. Używam tymczasowej bazy SQLite w: sqlite:///{db_path}")
        db_url = f"sqlite:///{db_path}"
    else:
        logger.warning("Brak skonfigurowanego połączenia z Supabase PostgreSQL. Następuje automatyczne przełączenie na bazę SQLite: sqlite:///./lojiparse.db")
        db_url = "sqlite:///./lojiparse.db"

connect_args = {}
# SQLite wymaga wyłączenia sprawdzania wątków w FastAPI
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Inicjalizacja silnika bazy danych
pool_kwargs = {}
if db_url.startswith("postgresql") and os.environ.get("VERCEL"):
    from sqlalchemy.pool import NullPool
    pool_kwargs["poolclass"] = NullPool

engine = create_engine(
    db_url,
    pool_pre_ping=True,
    connect_args=connect_args,
    **pool_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Zależność FastAPI zapewniająca sesję bazy danych dla każdego zapytania,
    automatycznie zamykająca ją po zakończeniu przetwarzania.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
