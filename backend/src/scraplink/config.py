from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .places import PLACES


class Settings(BaseSettings):
    # .env lives at the repository root; a backend-local .env overrides it.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str = "sqlite:///./scraplink-dev.db"

    @field_validator("database_url")
    @classmethod
    def _use_psycopg(cls, url: str) -> str:
        # Hosted Postgres (Neon on Vercel) hands out plain postgres:// URLs; the driver is psycopg.
        for scheme in ("postgres://", "postgresql://"):
            if url.startswith(scheme):
                return "postgresql+psycopg://" + url.removeprefix(scheme)
        return url

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
    # Set on Vercel (by connecting a Blob store): files then go to Vercel Blob, not MEDIA_DIR.
    blob_read_write_token: str = ""
    # Where people open the web client; certificate verify links point here.
    public_base_url: str = "http://localhost:5173"
    # 8081 is the Expo dev server, for the mobile app in a browser.
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8081"]

    # Escrow is funded at winning rate x declared weight x (1 + tolerance), so a weighbridge
    # reading up to this much above the declared weight still settles without a top-up.
    escrow_weight_tolerance: Decimal = Decimal("0.10")
    # A winning buyer has this long to pay into escrow; after that the lot passes to the next
    # highest bid, or ends unsold.
    escrow_funding_hours: int = Field(default=24, ge=1)
    # Width of the fair-price range shown around the point estimate.
    price_band: Decimal = Decimal("0.10")

    # Location in the estimate: a freight allowance off the price, per 10 km between the lot's
    # town and its nearest yard, capped. Illustrative until it is fitted to real transport costs.
    freight_bp_per_10_km: int = Field(default=20, ge=0)
    freight_max_bp: int = Field(default=1000, ge=0, le=5000)

    # Email for notifications. Empty SMTP_HOST logs each email instead of sending it.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "ScrapLink <no-reply@scraplink.local>"

    # Dynamic pricing (repricing.py). Each run moves a material's grade A reference price
    # `reprice_blend` of the way toward the median of recent paid trades (converted to grade A),
    # by at most `reprice_max_step` of the current price. It holds when there are fewer than
    # `reprice_min_trades` trades in the window, or the move would be under `reprice_min_move`.
    reprice_window_days: int = Field(default=30, ge=1)
    reprice_min_trades: int = Field(default=3, ge=1)
    reprice_blend: Decimal = Field(default=Decimal("0.5"), gt=0, le=1)
    reprice_max_step: Decimal = Field(default=Decimal("0.10"), gt=0, lt=1)
    reprice_min_move: Decimal = Field(default=Decimal("0.005"), ge=0)

    # The yards trucks leave from, as places.PLACES codes (YARDS='["kochi", "delhi"]'). A lot's
    # freight allowance is measured from its nearest yard, and each day's pickups are routed from
    # the yard nearest each one. The default network is illustrative, like the allowance.
    yards: list[str] = Field(
        default=[
            "kochi",
            "chennai",
            "bengaluru",
            "hyderabad",
            "visakhapatnam",
            "mumbai",
            "pune",
            "ahmedabad",
            "indore",
            "nagpur",
            "delhi",
            "ludhiana",
            "jaipur",
            "lucknow",
            "patna",
            "kolkata",
            "guwahati",
        ],
        min_length=1,
    )

    @field_validator("yards")
    @classmethod
    def _known_towns(cls, yards: list[str]) -> list[str]:
        unknown = [code for code in yards if code not in PLACES]
        if unknown:
            raise ValueError(f"not in the town list: {', '.join(unknown)}")
        return list(dict.fromkeys(yards))

    # The arq worker's queue (see worker.py). The API itself never needs Redis.
    redis_url: str = "redis://localhost:6379/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
