import hashlib
import hmac
import secrets
import time
from typing import Dict, Any, Optional

SECRET_KEY = "orbital_guard_flight_deck_secret_salt_2026"

ROLE_PERMISSIONS = {
    "student": {
        "role_name": "Student",
        "description": "Educational / flight trainee role. Full access to monitor telemetry, view baselines, study NASA SOPs, and run software simulations.",
        "can_redistribute_workload": False,
        "can_dispense_inventory": False,
        "can_resolve_incidents": False,
        "can_run_simulations": True,
        "can_trigger_drills": False
    },
    "tester": {
        "role_name": "Tester",
        "description": "Quality assurance & flight systems validator. Can execute all 5 software telemetry modes, run stress drills, and evaluate ML outlier models.",
        "can_redistribute_workload": True,
        "can_dispense_inventory": True,
        "can_resolve_incidents": False,
        "can_run_simulations": True,
        "can_trigger_drills": True
    },
    "faculty": {
        "role_name": "Faculty / Flight Director",
        "description": "Mission Commander & Clinical Supervisor. Authorized to approve operational workload handovers, sign off on medical dispensations, and resolve incidents.",
        "can_redistribute_workload": True,
        "can_dispense_inventory": True,
        "can_resolve_incidents": True,
        "can_run_simulations": True,
        "can_trigger_drills": True
    }
}

def hash_password(password: str, salt: str) -> str:
    """PBKDF2-HMAC-SHA256 password hashing. Zero plaintext storage."""
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations=100_000
    )
    return key.hex()

def verify_password(stored_hash: str, salt: str, password_attempt: str) -> bool:
    attempt_hash = hash_password(password_attempt, salt)
    return hmac.compare_digest(stored_hash, attempt_hash)

# Initial credential store with unique salts and PBKDF2 hashes
ACCOUNTS = {
    "student": {
        "username": "student",
        "name": "Astronaut Trainee",
        "role": "student",
        "salt": "salt_student_ast_2026",
        "hash": hash_password("Student2026!", "salt_student_ast_2026")
    },
    "tester": {
        "username": "tester",
        "name": "Systems Flight Tester",
        "role": "tester",
        "salt": "salt_tester_ast_2026",
        "hash": hash_password("Tester2026!", "salt_tester_ast_2026")
    },
    "faculty": {
        "username": "faculty",
        "name": "Prof. Flight Director",
        "role": "faculty",
        "salt": "salt_faculty_ast_2026",
        "hash": hash_password("Faculty2026!", "salt_faculty_ast_2026")
    }
}

# In-memory active session tokens
ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}
SESSION_LIFETIME_SECONDS = 28800  # 8 hours standard aerospace shift

def create_session_token(username: str, role: str, lifetime_seconds: int = SESSION_LIFETIME_SECONDS) -> str:
    token = secrets.token_hex(24)
    now = time.time()
    ACTIVE_SESSIONS[token] = {
        "username": username,
        "role": role,
        "created_at": now,
        "last_accessed_at": now,
        "expires_at": now + lifetime_seconds
    }
    return token

def validate_session(token: Optional[str]) -> Optional[Dict[str, Any]]:
    if not token or token not in ACTIVE_SESSIONS:
        return None
    session = ACTIVE_SESSIONS[token]
    now = time.time()
    if now > session["expires_at"]:
        del ACTIVE_SESSIONS[token]
        return None
    session["last_accessed_at"] = now
    return session

def revoke_session(token: Optional[str]) -> bool:
    if token and token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[token]
        return True
    return False

def clean_expired_sessions() -> int:
    now = time.time()
    expired = [t for t, s in ACTIVE_SESSIONS.items() if now > s["expires_at"]]
    for t in expired:
        del ACTIVE_SESSIONS[t]
    return len(expired)

class RateLimiter:
    """Sliding-window in-memory rate limiter for mission deck endpoints."""
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._history: Dict[str, list] = {}

    def is_allowed(self, client_key: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        if client_key not in self._history:
            self._history[client_key] = []
        # Filter older timestamps
        self._history[client_key] = [t for t in self._history[client_key] if t > cutoff]
        if len(self._history[client_key]) >= self.max_requests:
            return False
        self._history[client_key].append(now)
        return True

# Rate limiters for authentication & sensitive endpoints
auth_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
api_rate_limiter = RateLimiter(max_requests=120, window_seconds=60)

def sanitize_text(text: Optional[str], max_len: int = 500) -> str:
    """Sanitizes user input string against HTML and script injection."""
    if not text:
        return ""
    clean = str(text).replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    return clean[:max_len]

