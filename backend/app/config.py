from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = Field(validation_alias=AliasChoices("NEON_DATABASE_URL", "DATABASE_URL"))
    jwt_secret: str
    fernet_key: str
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"

    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    admin_emails: str = ""  # comma-separated emails granted /admin access

    tavily_api_key: str = ""  # primary web search; DuckDuckGo fallback when unset

    coupon_code: str = "SID_DRDROID"
    signup_credits: int = 5


settings = Settings()
