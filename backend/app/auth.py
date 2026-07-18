from datetime import datetime, timedelta, timezone

import jwt
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
oauth.register(
    name="github",
    client_id=settings.github_client_id,
    client_secret=settings.github_client_secret,
    access_token_url="https://github.com/login/oauth/access_token",
    authorize_url="https://github.com/login/oauth/authorize",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "read:user user:email"},
)

JWT_ALGORITHM = "HS256"
ACCESS_TTL = timedelta(minutes=30)
REFRESH_TTL = timedelta(days=30)


def _token(user_id: str, ttl: timedelta, kind: str) -> str:
    payload = {"sub": user_id, "type": kind, "exp": datetime.now(timezone.utc) + ttl}
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def create_access_token(user_id: str) -> str:
    return _token(user_id, ACCESS_TTL, "access")


def create_refresh_token(user_id: str) -> str:
    return _token(user_id, REFRESH_TTL, "refresh")


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(401, "Missing bearer token")
    try:
        payload = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")
    if payload.get("type") != "access":
        raise HTTPException(401, "Invalid or expired token")
    user = db.get(User, payload["sub"])
    if user is None:
        raise HTTPException(401, "User not found")
    return user


class RefreshIn(BaseModel):
    refresh_token: str


@router.post("/refresh")
def refresh_tokens(body: RefreshIn, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(body.refresh_token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(401, "Not a refresh token")
    if db.get(User, payload["sub"]) is None:
        raise HTTPException(401, "User not found")
    return {"access_token": create_access_token(payload["sub"]), "refresh_token": create_refresh_token(payload["sub"])}


def _upsert_user(db: Session, *, email: str, name: str, avatar_url: str, provider: str) -> User:
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None:
        user = User(email=email, name=name, avatar_url=avatar_url, provider=provider)
        db.add(user)
    else:
        user.name = name or user.name
        user.avatar_url = avatar_url or user.avatar_url
    db.commit()
    db.refresh(user)
    return user


@router.get("/{provider}/login")
async def login(provider: str, request: Request):
    if provider not in ("google", "github"):
        raise HTTPException(404, "Unknown provider")
    client = oauth.create_client(provider)
    redirect_uri = f"{settings.backend_url}/auth/{provider}/callback"
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/{provider}/callback")
async def callback(provider: str, request: Request, db: Session = Depends(get_db)):
    if provider not in ("google", "github"):
        raise HTTPException(404, "Unknown provider")
    client = oauth.create_client(provider)
    token = await client.authorize_access_token(request)

    if provider == "google":
        info = token.get("userinfo") or await client.userinfo(token=token)
        email, name, avatar_url = info["email"], info.get("name", ""), info.get("picture", "")
    else:
        profile = (await client.get("user", token=token)).json()
        email = profile.get("email")
        if not email:
            emails = (await client.get("user/emails", token=token)).json()
            primary = next((e for e in emails if e.get("primary")), emails[0] if emails else None)
            email = primary["email"] if primary else f"{profile['id']}@users.noreply.github.com"
        name, avatar_url = profile.get("name") or profile.get("login", ""), profile.get("avatar_url", "")

    user = _upsert_user(db, email=email, name=name, avatar_url=avatar_url, provider=provider)
    return RedirectResponse(
        f"{settings.frontend_url}/auth/callback#token={create_access_token(user.id)}&refresh={create_refresh_token(user.id)}"
    )
