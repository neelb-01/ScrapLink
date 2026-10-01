import hashlib
import hmac
import uuid
from typing import Protocol

import httpx


class PaymentGateway(Protocol):
    name: str

    def create_order(self, amount_paise: int, receipt: str) -> str:
        """Create an order on the rail and return its id."""
        ...


class SimulatedGateway:
    """Confirms payments without moving money. For local development and demos only."""

    name = "simulated"

    def create_order(self, amount_paise: int, receipt: str) -> str:
        return f"sim_order_{uuid.uuid4().hex}"


class RazorpayGateway:
    name = "razorpay"

    def __init__(self, key_id: str, key_secret: str, timeout_seconds: float = 10.0):
        if not key_id or not key_secret:
            raise RuntimeError("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET are required")
        self.key_id = key_id
        self._secret = key_secret
        self._http = httpx.Client(
            base_url="https://api.razorpay.com/v1",
            auth=(key_id, key_secret),
            timeout=timeout_seconds,
        )

    def create_order(self, amount_paise: int, receipt: str) -> str:
        response = self._http.post(
            "/orders",
            json={"amount": amount_paise, "currency": "INR", "receipt": receipt[:40]},
        )
        response.raise_for_status()
        return response.json()["id"]

    def verify_checkout(self, order_id: str, payment_id: str, signature: str) -> bool:
        """Checkout's success handler returns HMAC-SHA256("order_id|payment_id", key secret)."""
        body = f"{order_id}|{payment_id}".encode()
        return verify_razorpay_signature(body, signature, self._secret)


def verify_razorpay_signature(body: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
