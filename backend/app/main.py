from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app import admin, billing, threads, stats, llm_settings
from app.auth import get_current_user, router as auth_router
from app.config import settings
from app.db import Base, engine
from app.models import User  # noqa: F401 - ensures all models are registered before create_all

Base.metadata.create_all(bind=engine)

# create_all doesn't alter existing tables; add the soft-delete column to already-deployed DBs.
with engine.begin() as conn:
    try:
        conn.exec_driver_sql("ALTER TABLE threads ADD COLUMN deleted BOOLEAN DEFAULT FALSE")
    except Exception:  # noqa: BLE001 - column already exists
        pass

app = FastAPI(title="MicroManus")

app.add_middleware(SessionMiddleware, secret_key=settings.jwt_secret)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin.router)
app.include_router(billing.router)
app.include_router(llm_settings.router)
app.include_router(threads.router)
app.include_router(stats.router)


@app.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "credits": user.credits,
        "has_access": user.has_access,
        "is_admin": admin.is_admin(user),
    }


@app.get("/health")
def health():
    return {"status": "ok"}
