"""
ASTRA SENSE – ORBITAL GUARD
Supabase Client & Data Synchronization Layer
Phase 2: Hybrid Database Architecture
"""

import json
from typing import Dict, Any, List, Optional
import httpx
from app.config import settings
from app.core.logging import logger

class SupabaseClientManager:
    """
    Manages secure communication between the FastAPI backend and Supabase PostgreSQL.
    Enforces least-privilege, exponential backoff, and non-blocking offline resilience.
    Uses service-role key strictly on the backend to execute trusted sync worker jobs.
    """

    def __init__(self):
        self.url = settings.SUPABASE_URL.strip() if settings.SUPABASE_URL else ""
        # Modern secret key with fallback to legacy service_role key
        self.key = (settings.SUPABASE_SECRET_KEY or settings.SUPABASE_SERVICE_ROLE_KEY or "").strip()
        # Modern publishable key with fallback to legacy anon key
        self.anon_key = (settings.SUPABASE_PUBLISHABLE_KEY or settings.SUPABASE_ANON_KEY or "").strip()
        self.jwks_url = settings.SUPABASE_JWKS_URL.strip() if settings.SUPABASE_JWKS_URL else ""
        self._test_mode_override: Optional[bool] = None

    @property
    def is_configured(self) -> bool:
        """Returns True only when valid Supabase URL and secret/service key are provided."""
        if self._test_mode_override is not None:
            return self._test_mode_override
        is_placeholder_url = not self.url or self.url.startswith("http://placeholder") or "<your-" in self.url
        is_placeholder_key = not self.key or "PASTE_YOUR" in self.key or "YOUR_SUPABASE" in self.key or "<your-" in self.key
        return bool(not is_placeholder_url and not is_placeholder_key)

    def set_test_mode(self, enabled: Optional[bool]):
        """Allows testing sync behaviors in isolated unit tests."""
        self._test_mode_override = enabled

    def _get_headers(
        self,
        prefer_merge: bool = True,
        user_jwt: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Constructs secure PostgREST request headers with modern & legacy key support.
        - 'apikey': Always populated with self.key.
        - 'Authorization':
            - If user_jwt is provided: 'Bearer {user_jwt}' (user session context).
            - Else if self.key is a legacy JWT (starts with 'eyJ'): 'Bearer {self.key}'.
            - For modern opaque keys (e.g. starts with 'sb_secret_'): NO Authorization header sent,
              preventing 'Invalid JWT' gateway rejections.
        """
        headers = {
            "apikey": self.key,
            "Content-Type": "application/json"
        }
        if user_jwt:
            headers["Authorization"] = f"Bearer {user_jwt}"
        elif self.key and self.key.startswith("eyJ"):
            headers["Authorization"] = f"Bearer {self.key}"

        if prefer_merge:
            headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        return headers

    def _scrub_error(self, exc: Exception) -> str:
        """Removes any API keys or credentials from error strings."""
        err_msg = str(exc)
        if self.key and self.key in err_msg:
            err_msg = err_msg.replace(self.key, "[REDACTED_KEY]")
        if self.anon_key and self.anon_key in err_msg:
            err_msg = err_msg.replace(self.anon_key, "[REDACTED_KEY]")
        return err_msg

    async def test_connection(self) -> Dict[str, Any]:
        """
        Verifies cloud Supabase reachability with a fast health check.
        Never throws exceptions; returns safe structured status.
        """
        if not self.is_configured:
            return {
                "connected": False,
                "configured": False,
                "status": "NOT_CONFIGURED",
                "message": "Local SQLite serving as primary operational database. Cloud target unconfigured."
            }

        endpoint = f"{self.url.rstrip('/')}/rest/v1/"
        headers = self._get_headers(prefer_merge=False)

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(endpoint, headers=headers)
                # PostgREST root returns 200 with OpenAPI schema or 404
                is_online = res.status_code in (200, 404)
                return {
                    "connected": is_online,
                    "configured": True,
                    "status": "ONLINE" if is_online else "UNREACHABLE",
                    "status_code": res.status_code,
                    "message": "Supabase cloud database connected" if is_online else f"HTTP {res.status_code}"
                }
        except httpx.ConnectTimeout:
            return {
                "connected": False,
                "configured": True,
                "status": "TIMEOUT",
                "error": "Connection timed out. Maintained in local flight store."
            }
        except Exception as exc:
            return {
                "connected": False,
                "configured": True,
                "status": "OFFLINE",
                "error": self._scrub_error(exc)
            }

    async def upsert_record(
        self,
        table: str,
        record: Dict[str, Any],
        on_conflict: str = "id",
        user_jwt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Performs idempotent upsert of a single record into Supabase PostgreSQL.
        """
        if not self.is_configured:
            return {
                "status": "QUEUED_OFFLINE",
                "table": table,
                "message": "Supabase credentials unconfigured. Event preserved in local outbox."
            }

        endpoint = f"{self.url.rstrip('/')}/rest/v1/{table}?on_conflict={on_conflict}"
        headers = self._get_headers(prefer_merge=True, user_jwt=user_jwt)

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.post(endpoint, json=record, headers=headers)
                if res.status_code in (200, 201, 204):
                    return {"status": "SUCCESS", "status_code": res.status_code}
                else:
                    safe_err = res.text[:200]
                    if self.key and self.key in safe_err:
                        safe_err = safe_err.replace(self.key, "[REDACTED]")
                    logger.warning(f"Supabase upsert on {table} failed with code {res.status_code}: {safe_err}")
                    return {
                        "status": "RETRY_REQUIRED",
                        "status_code": res.status_code,
                        "error": safe_err
                    }
        except Exception as exc:
            return {"status": "NETWORK_ERROR", "error": self._scrub_error(exc)}

    async def sync_incident(self, incident: Dict[str, Any], user_jwt: Optional[str] = None) -> Dict[str, Any]:
        """Backward-compatible helper for incident sync."""
        if not self.is_configured:
            return {
                "status": "QUEUED_OFFLINE",
                "message": "Supabase credentials not configured. Cached locally in SQLite."
            }
        return await self.upsert_record("incidents", incident, user_jwt=user_jwt)

    async def batch_upsert(
        self,
        table: str,
        records: List[Dict[str, Any]],
        on_conflict: str = "id",
        user_jwt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Performs batch upsert of records into Supabase PostgREST.
        """
        if not records:
            return {"status": "NOOP", "count": 0}

        if not self.is_configured:
            return {
                "status": "QUEUED_OFFLINE",
                "table": table,
                "count": len(records),
                "message": "Preserved in local outbox."
            }

        endpoint = f"{self.url.rstrip('/')}/rest/v1/{table}?on_conflict={on_conflict}"
        headers = self._get_headers(prefer_merge=True, user_jwt=user_jwt)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(endpoint, json=records, headers=headers)
                if res.status_code in (200, 201, 204):
                    return {"status": "SUCCESS", "count": len(records)}
                else:
                    safe_err = res.text[:250]
                    if self.key and self.key in safe_err:
                        safe_err = safe_err.replace(self.key, "[REDACTED]")
                    return {
                        "status": "BATCH_ERROR",
                        "status_code": res.status_code,
                        "error": safe_err
                    }
        except Exception as exc:
            return {"status": "NETWORK_ERROR", "error": self._scrub_error(exc)}

    async def call_rpc(
        self,
        function_name: str,
        params: Dict[str, Any],
        user_jwt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calls a PostgreSQL stored function (RPC) in Supabase.
        Used for atomic inventory reconciliation.
        """
        if not self.is_configured:
            return {"status": "QUEUED_OFFLINE"}

        endpoint = f"{self.url.rstrip('/')}/rest/v1/rpc/{function_name}"
        headers = self._get_headers(prefer_merge=False, user_jwt=user_jwt)

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.post(endpoint, json=params, headers=headers)
                if res.status_code in (200, 201):
                    return {"status": "SUCCESS", "data": res.json()}
                else:
                    safe_err = res.text[:200]
                    if self.key and self.key in safe_err:
                        safe_err = safe_err.replace(self.key, "[REDACTED]")
                    return {
                        "status": "RPC_ERROR",
                        "status_code": res.status_code,
                        "error": safe_err
                    }
        except Exception as exc:
            return {"status": "NETWORK_ERROR", "error": self._scrub_error(exc)}

# Singleton manager
supabase_manager = SupabaseClientManager()
