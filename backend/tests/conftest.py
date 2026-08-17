import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.catalog import ClothType, DesignOption, DesignOptionGroup, Material, MaterialColor
from app.models.user import User

# In-memory SQLite shared across connections in this test session (StaticPool
# keeps a single connection alive so the in-memory DB doesn't vanish between
# requests). This is why every JSON-ish column in app/models uses plain
# sqlalchemy.JSON rather than a Postgres-only type — it must run on SQLite.
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True, scope="session")
def isolate_from_developer_env():
    """Force external integrations off for the whole test session.

    Settings are loaded from .env, so without this the suite behaves
    differently depending on what the developer happens to have configured —
    and once real model repos are set it will actually download hundreds of
    megabytes from the Hugging Face Hub mid-test.

    CI must exercise the graceful-degradation path anyway, since that is what
    protects the deployed app when a provider is cold or rate-limited.
    """
    from app.core.config import settings
    from app.services import ml as ml_service

    original = {
        "ml_enabled": settings.ml_enabled,
        "hf_username": settings.hf_username,
        "hf_classifier_model": settings.hf_classifier_model,
        "hf_measurement_model": settings.hf_measurement_model,
        "hf_fit_model": settings.hf_fit_model,
        "cf_account_id": settings.cf_account_id,
        "cf_api_token": settings.cf_api_token,
        "hf_token": settings.hf_token,
    }
    for key in original:
        setattr(settings, key, False if key == "ml_enabled" else None)

    # Drop anything a previous run cached, so state can't leak between tests.
    ml_service.reset_cache()

    yield

    for key, value in original.items():
        setattr(settings, key, value)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded_catalog(db_session):
    """Minimal catalogue fixture — one cloth type, one material with stock,
    one design option — enough to exercise the order-creation path without
    running the full seed script."""
    cloth_type = ClothType(
        slug="tshirt",
        name="T-shirt",
        base_price=2200,
        base_stitching_cost=300,
        base_fabric_metres=1.4,
        reference_body_cm=96,
        ai_prompt_noun="t-shirt",
    )
    db_session.add(cloth_type)
    db_session.flush()

    material = Material(
        slug="cotton",
        name="Cotton",
        cost_per_metre=650,
        stock_metres=10,
        low_stock_threshold=5,
        ai_prompt_term="cotton",
    )
    db_session.add(material)
    db_session.flush()

    color = MaterialColor(material_id=material.id, name="Ivory", hex_code="#F5F0E8", ai_prompt_term="ivory")
    db_session.add(color)

    group = DesignOptionGroup(cloth_type_id=None, code="sleeve", label="Sleeve", selection_type="single")
    db_session.add(group)
    db_session.flush()
    option = DesignOption(
        group_id=group.id,
        code="puffed_sleeve",
        label="Puffed sleeve",
        ai_prompt_term="puffed sleeves",
        stitching_premium=300,
        fabric_multiplier=1.20,
    )
    db_session.add(option)
    db_session.commit()

    return {"cloth_type": cloth_type, "material": material, "color": color, "option": option}


@pytest.fixture()
def registered_user(db_session):
    user = User(
        first_name="Test",
        last_name="User",
        email="test@example.com",
        password_hash=get_password_hash("password123"),
        role="customer",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture()
def admin_user(db_session):
    user = User(
        first_name="Admin",
        last_name="User",
        email="admin@example.com",
        password_hash=get_password_hash("adminpass123"),
        role="admin",
    )
    db_session.add(user)
    db_session.commit()
    return user


def auth_headers(client: TestClient, email: str, password: str) -> dict:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
