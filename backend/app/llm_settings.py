from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.crypto import encrypt
from app.db import get_db
from app.models import LLMConfig, User
from app.pricing import MODELS, PROVIDER_DEFAULT_BASE_URL
from app.schemas import LLMConfigIn, LLMConfigOut

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/models")
def list_models():
    return [{"id": mid, "provider": info.provider, "label": info.label} for mid, info in MODELS.items()]


@router.get("/llm", response_model=LLMConfigOut | None)
def get_llm_config(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cfg = db.query(LLMConfig).filter(LLMConfig.user_id == user.id).one_or_none()
    if cfg is None:
        return None
    return LLMConfigOut(provider=cfg.provider, model=cfg.model, base_url=cfg.base_url, key_set=True)


@router.put("/llm", response_model=LLMConfigOut)
def upsert_llm_config(body: LLMConfigIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.model not in MODELS:
        raise HTTPException(400, f"Unsupported model: {body.model}")
    if MODELS[body.model].provider != body.provider:
        raise HTTPException(400, "Model does not match provider")
    keys = [k.strip() for k in body.api_key.split(",") if k.strip()]
    if not keys:
        raise HTTPException(400, "API key is required (one key, or several comma-separated keys to rotate)")

    base_url = body.base_url or PROVIDER_DEFAULT_BASE_URL[body.provider]
    cfg = db.query(LLMConfig).filter(LLMConfig.user_id == user.id).one_or_none()
    if cfg is None:
        cfg = LLMConfig(user_id=user.id)
        db.add(cfg)
    cfg.provider = body.provider
    cfg.model = body.model
    cfg.base_url = base_url
    cfg.encrypted_api_key = encrypt(body.api_key)
    db.commit()
    return LLMConfigOut(provider=cfg.provider, model=cfg.model, base_url=cfg.base_url, key_set=True)
