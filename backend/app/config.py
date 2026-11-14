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

    # Database configuration & path resolution
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    @property
    def DATABASE_PATH(self) -> Path:
        # 1. Explicit DATABASE_URL handling (supports sqlite:////data/... or sqlite:///./...)
        if self.DATABASE_URL:
            raw = self.DATABASE_URL
            if raw.startswith("sqlite:////"):
                return Path("/" + raw[len("sqlite:////"):])
            elif raw.startswith("sqlite:///"):
                path_part = raw[len("sqlite:///"):]
                p = Path(path_part)
                if not p.is_absolute():
                    p = (BASE_DIR / path_part).resolve()
                return p
            elif raw.startswith("sqlite://"):
                path_part = raw[len("sqlite://"):]
                p = Path(path_part)
                if not p.is_absolute():
                    p = (BASE_DIR / path_part).resolve()
                return p

        # 2. Railway persistent volume auto-detection (/data mount)
        data_dir = Path("/data")
        if data_dir.exists() and os.access(data_dir, os.W_OK):
            return data_dir / "orbital_guard.db"

        # 3. Fail clearly if production environment requires persistent volume but it is missing
        if self.ENVIRONMENT in ("production", "railway") and os.getenv("RAILWAY_ENVIRONMENT"):
            if not data_dir.exists() or not os.access(data_dir, os.W_OK):
                raise RuntimeError("CRITICAL: Production Railway volume /data is missing or non-writable! Ephemeral fallback forbidden.")
            return data_dir / "orbital_guard.db"

        # 4. Local flight default
        return BASE_DIR / "orbital_guard.db"

    @property
    def STATIC_DIR(self) -> Path:
        custom = os.getenv("STATIC_DIR")
        if custom and Path(custom).exists():
            return Path(custom)
        candidates = [
            BASE_DIR.parent / "dist",     # Root dist/ directory
            Path("/app/dist"),            # Docker container dist
            Path("/app/static"),          # Docker container static
            BASE_DIR / "static"           # Backend static directory
        ]
        for c in candidates:
            if c.exists() and (c / "index.html").exists():
                return c
        return BASE_DIR.parent / "dist"

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
