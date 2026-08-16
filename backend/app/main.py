from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.routers import (
    auth,
    catalog,
    dashboard,
    designs,
    health,
    measurements,
    ml,
    mockup,
    orders,
    quote,
    uploads,
)
from app.routers.admin import catalog as admin_catalog
from app.routers.admin import inventory as admin_inventory
from app.routers.admin import orders as admin_orders
from app.services.storage import LOCAL_STATIC_DIR


def create_app() -> FastAPI:
    app = FastAPI(title="ThreadCraft API")

    # Explicit origin allowlist. The previous config used allow_origins=["*"]
    # together with allow_credentials=True — an invalid combination per the
    # CORS spec that browsers reject outright. Auth here is a Bearer header,
    # not a cookie, so allow_credentials stays False regardless.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Serves generated mockups and uploaded reference images when object
    # storage isn't configured, so the app is fully functional with no
    # third-party accounts.
    LOCAL_STATIC_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/static/generated", StaticFiles(directory=str(LOCAL_STATIC_DIR)), name="generated")

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(catalog.router)
    app.include_router(measurements.router)
    app.include_router(quote.router)
    app.include_router(orders.router)
    app.include_router(designs.router)
    app.include_router(dashboard.router)
    app.include_router(mockup.router)
    app.include_router(uploads.router)
    app.include_router(ml.router)
    app.include_router(admin_catalog.router)
    app.include_router(admin_inventory.router)
    app.include_router(admin_orders.router)

    return app


app = create_app()
