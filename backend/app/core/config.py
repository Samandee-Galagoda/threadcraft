import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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
    #
    # NoDecode disables pydantic-settings' automatic JSON parsing of this field
    # so the validator below sees the raw string. Without it, a CORS_ORIGINS
    # that isn't valid JSON raises SettingsError while Settings is being
    # constructed — which happens at import time, so the process exits before
    # the app starts and the only symptom is a crash-looping deploy. Pasting a
    # bare URL into a hosting dashboard is the obvious thing to do and is
    # exactly what triggers it, so the field accepts all three sane spellings:
    #   ["https://a.app","https://b.app"]   JSON array
    #   https://a.app, https://b.app        comma-separated
    #   https://a.app                       a single origin
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    # Vercel gives every preview deployment its own hostname, so they can't be
    # enumerated in the list above. A regex covers them, e.g.
    #   https://threadcraft-.*\.vercel\.app
    cors_origin_regex: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value):
        """Accept a JSON array, a comma-separated list, or a single origin.

        Trailing slashes are stripped because CORS matching is on the exact
        origin: "https://app.vercel.app/" never matches the browser's
        "https://app.vercel.app", and the resulting failure looks like a
        server bug rather than a typo in a dashboard field.
        """
        if value is None or isinstance(value, list):
            origins = value or []
        else:
            text = str(value).strip()
            if text.startswith("["):
                try:
                    origins = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"CORS_ORIGINS looks like JSON but could not be parsed: {exc}. "
                        'Expected e.g. ["https://your-app.vercel.app"]'
                    ) from exc
            else:
                origins = text.split(",")

        return [origin.strip().rstrip("/") for origin in origins if str(origin).strip()]

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
    # Cancelling returns to the success page, which detects the unpaid order
    # and offers to resume — the wizard has already been reset by then, so
    # sending them back to step 5 would show an empty form.
    checkout_cancel_url: str = "http://localhost:5173/success"

    # Email
    resend_api_key: str | None = None
    mail_from: str = "ThreadCraft <onboarding@resend.dev>"

    # Trained ML models on the Hugging Face Hub.
    # Set HF_USERNAME and the three repo IDs default to the notebooks' output names;
    # override any of them explicitly if you renamed a repo.
    hf_username: str | None = None
    hf_classifier_model: str | None = None
    hf_measurement_model: str | None = None
    hf_fit_model: str | None = None
    ml_enabled: bool = True  # set False to disable model loading entirely
    # The ViT classifier is ~350 MB — more than a 512 MB free-tier instance can
    # comfortably hold alongside the app, so it is gated separately from the two
    # small scikit-learn models.
    ml_enable_classifier: bool = False

    @property
    def classifier_repo(self) -> str | None:
        if self.hf_classifier_model:
            return self.hf_classifier_model
        return f"{self.hf_username}/threadcraft-garment-classifier" if self.hf_username else None

    @property
    def measurement_repo(self) -> str | None:
        if self.hf_measurement_model:
            return self.hf_measurement_model
        return f"{self.hf_username}/threadcraft-measurement-predictor" if self.hf_username else None

    @property
    def fit_repo(self) -> str | None:
        if self.hf_fit_model:
            return self.hf_fit_model
        return f"{self.hf_username}/threadcraft-fit-recommender" if self.hf_username else None

    # Seed data
    admin_email: str = "admin@threadcraft.lk"
    admin_password: str = "ChangeMe123!"
    demo_email: str = "demo@threadcraft.lk"
    demo_password: str = "Demo1234!"


settings = Settings()
