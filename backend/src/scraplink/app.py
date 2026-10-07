import logging
from collections.abc import Callable
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .classification import Classifier, classifier_from_url
from .config import Settings, get_settings
from .db import make_engine, make_sessionmaker
from .env import Env
from .errors import DomainError
from .models import utcnow
from .payments import PaymentGateway, RazorpayGateway, SimulatedGateway
from .routers import (
    agreements,
    auth,
    catalogue,
    certificates,
    impact,
    lots,
    operations,
    payments,
    rfqs,
    wallet,
)
from .storage import LocalStorage, Storage

log = logging.getLogger(__name__)


def gateway_from_settings(settings: Settings) -> PaymentGateway:
    if settings.payment_gateway == "razorpay":
        return RazorpayGateway(settings.razorpay_key_id, settings.razorpay_key_secret)
    log.warning("PAYMENT_GATEWAY=simulated: escrow is funded without moving money")
    return SimulatedGateway()


def create_app(
    settings: Settings | None = None,
    *,
    clock: Callable[[], datetime] | None = None,
    classifier: Classifier | None = None,
    storage: Storage | None = None,
    gateway: PaymentGateway | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET must be set (see .env.example)")

    engine = make_engine(settings.database_url)
    app = FastAPI(title="ScrapLink", version=__version__)
    app.state.engine = engine
    app.state.sessionmaker = make_sessionmaker(engine)
    app.state.env = Env(
        settings=settings,
        clock=clock or utcnow,
        classifier=classifier or classifier_from_url(settings.ml_service_url),
        storage=storage or LocalStorage(settings.media_dir),
        gateway=gateway or gateway_from_settings(settings),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    async def _domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    for module in (auth, catalogue, lots, payments, certificates, wallet, rfqs, agreements, impact):
        app.include_router(module.router)
    app.include_router(catalogue.admin)
    app.include_router(operations.router)
    return app
