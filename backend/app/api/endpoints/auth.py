from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from app.core.auth import (
    ACCOUNTS, ROLE_PERMISSIONS, verify_password,
    create_session_token, validate_session, ACTIVE_SESSIONS
)

router = APIRouter()

class LoginRequest(BaseModel):
    username: str = Field(..., description="student | tester | faculty")
    password: str = Field(..., description="Role authentication password")

class LoginResponse(BaseModel):
    status: str
    token: str
    username: str
    name: str
    role: str
    permissions: Dict[str, Any]

@router.post("/auth/login", response_model=LoginResponse, summary="Local role-based authentication")
def login(req: LoginRequest):
    uname = req.username.strip().lower()
    if uname not in ACCOUNTS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Use 'student', 'tester', or 'faculty'."
        )

    acc = ACCOUNTS[uname]
    if not verify_password(acc["hash"], acc["salt"], req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password for specified role."
        )

    token = create_session_token(uname, acc["role"])
    perms = ROLE_PERMISSIONS.get(acc["role"], {})

    return LoginResponse(
        status="AUTHENTICATED",
        token=token,
        username=uname,
        name=acc["name"],
        role=acc["role"],
        permissions=perms
    )

@router.get("/auth/me", summary="Check current session and permissions")
def get_current_user(authorization: Optional[str] = Header(None)):
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]

    session = validate_session(token)
    if not session:
        # Default to student guest session for seamless offline usability
        return {
            "authenticated": False,
            "username": "guest_student",
            "name": "Astronaut Trainee (Guest)",
            "role": "student",
            "permissions": ROLE_PERMISSIONS["student"]
        }

    acc = ACCOUNTS[session["username"]]
    return {
        "authenticated": True,
        "username": session["username"],
        "name": acc["name"],
        "role": session["role"],
        "permissions": ROLE_PERMISSIONS.get(session["role"], {})
    }

@router.post("/auth/logout", summary="Terminate active session")
def logout(authorization: Optional[str] = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        ACTIVE_SESSIONS.pop(token, None)
    return {"status": "LOGGED_OUT"}

@router.get("/auth/roles", summary="Get supported roles description")
def get_roles():
    return ROLE_PERMISSIONS

