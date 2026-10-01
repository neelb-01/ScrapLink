from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env lives at the repository root; a backend-local .env overrides it.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str = "sqlite:///./scraplink-dev.db"

    jwt_secret: str = ""
    jwt_access_ttl_seconds: int = 900

    # Empty disables the ML service: every lot then needs manual category selection.
    ml_service_url: str = ""
    ml_classification_confidence_threshold: float = 0.75

    # "simulated" confirms payments without moving money. Pilot and production use "razorpay".
    payment_gateway: Literal["simulated", "razorpay"] = "simulated"
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    media_dir: str = "./media"
    # Where people open the web client; certificate verify links point here.
    public_base_url: str = "http://localhost:5173"
    cors_origins: list[str] = ["http://localhost:5173"]

    # Escrow is funded at winning rate x declared weight x (1 + tolerance), so a weighbridge
    # reading up to this much above the declared weight still settles without a top-up.
    escrow_weight_tolerance: Decimal = Decimal("0.10")
    # A winning buyer has this long to pay into escrow; after that the lot passes to the next
    # highest bid, or ends unsold.
    escrow_funding_hours: int = Field(default=24, ge=1)
    # Width of the fair-price range shown around the point estimate.
    price_band: Decimal = Decimal("0.10")


@lru_cache
def get_settings() -> Settings:
    return Settings()
