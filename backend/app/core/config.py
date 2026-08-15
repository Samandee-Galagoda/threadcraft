from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"

    # Database
    database_url: str = "sqlite:///./threadcraft.db"

    # Auth
    jwt_secret: str = "dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    # CORS — explicit origin list; never "*" (this app uses Bearer auth, not cookies,
    # so allow_credentials stays False and a wildcard origin is unnecessary anyway)
    cors_origins: list[str] = ["http://localhost:5173"]

    # AI mockup generation
    cf_account_id: str | None = None
    cf_api_token: str | None = None
    cf_image_model: str = "@cf/black-forest-labs/flux-1-schnell"
    hf_token: str | None = None
    hf_image_model: str = "black-forest-labs/FLUX.1-schnell"
    mockup_timeout_seconds: int = 30

    # Object storage (Cloudflare R2 — S3-compatible)
    r2_account_id: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_bucket: str = "threadcraft"
    r2_public_base_url: str | None = None
    upload_dir: Path = Path("uploads")  # local fallback when R2 isn't configured
    max_upload_bytes: int = 5 * 1024 * 1024
    max_reference_images: int = 3

    # Payments
    stripe_secret_key: str | None = None
    stripe_publishable_key: str | None = None
    checkout_success_url: str = "http://localhost:5173/success"
    checkout_cancel_url: str = "http://localhost:5173/design/step/5"

    # Email
    resend_api_key: str | None = None
    mail_from: str = "ThreadCraft <onboarding@resend.dev>"

    # Seed data
    admin_email: str = "admin@threadcraft.lk"
    admin_password: str = "ChangeMe123!"
    demo_email: str = "demo@threadcraft.lk"
    demo_password: str = "Demo1234!"


settings = Settings()
