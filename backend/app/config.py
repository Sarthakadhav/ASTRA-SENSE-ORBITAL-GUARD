import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    PROJECT_NAME: str = "ORBITAL GUARD / ASTRA SENSE"
    VERSION: str = "2.0.0"
    DESCRIPTION: str = (
        "AI-Powered Health Monitoring & Autonomous Medical Decision Support "
        "for Astronauts on Long-Duration Deep Space Missions"
    )
    API_V1_STR: str = "/api/v1"
    
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "flight_simulation")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

    # Local SQLite flight storage (primary offline-first engine)
    DATABASE_PATH: Path = BASE_DIR / "orbital_guard.db"

    # AI Intelligence keys (optional cloud enhancement)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # Supabase cloud sync (Phase 2 & Phase 2.5 hybrid database target)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    
    # Modern & Legacy Secret Key resolution (backend sync worker)
    # Checks SUPABASE_SECRET_KEY first, falls back to legacy SUPABASE_SERVICE_ROLE_KEY
    SUPABASE_SECRET_KEY: str = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = SUPABASE_SECRET_KEY  # Backward-compatible alias
    
    # Modern & Legacy Publishable/Anon Key resolution (optional client/public key)
    # Checks SUPABASE_PUBLISHABLE_KEY first, falls back to legacy SUPABASE_ANON_KEY
    SUPABASE_PUBLISHABLE_KEY: str = os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_ANON_KEY: str = SUPABASE_PUBLISHABLE_KEY  # Backward-compatible alias
    
    # Optional JWKS URL for asymmetric JWT verification
    SUPABASE_JWKS_URL: str = os.getenv("SUPABASE_JWKS_URL", "")

    SUPABASE_DB_URL: str = os.getenv("SUPABASE_DB_URL", "")
    SUPABASE_SYNC_ENABLED: bool = os.getenv("SUPABASE_SYNC_ENABLED", "True").lower() in ("true", "1", "yes")
    SUPABASE_SYNC_INTERVAL_SECONDS: int = int(os.getenv("SUPABASE_SYNC_INTERVAL_SECONDS", "10"))
    SUPABASE_SYNC_BATCH_SIZE: int = int(os.getenv("SUPABASE_SYNC_BATCH_SIZE", "50"))
    SUPABASE_MAX_RETRIES: int = int(os.getenv("SUPABASE_MAX_RETRIES", "5"))

    # Deep Space Network simulated delay
    DSN_LATENCY_SECONDS: int = int(os.getenv("DSN_LATENCY_SECONDS", "862"))
    DEFAULT_MET_DAYS: int = int(os.getenv("DEFAULT_MET_DAYS", "142"))

settings = Settings()
