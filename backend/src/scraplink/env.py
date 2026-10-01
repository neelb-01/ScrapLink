from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from .classification import Classifier
from .config import Settings
from .payments import PaymentGateway
from .storage import Storage


@dataclass
class Env:
    """Everything a service call needs besides the database session. Swapped wholesale in tests."""

    settings: Settings
    clock: Callable[[], datetime]
    classifier: Classifier
    storage: Storage
    gateway: PaymentGateway

    def now(self) -> datetime:
        return self.clock()
