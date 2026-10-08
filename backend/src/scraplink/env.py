from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from .classification import Classifier
from .config import Settings
from .payments import PaymentGateway
from .storage import Storage

if TYPE_CHECKING:
    from .notifications import Mailer


def _log_mailer():
    from .notifications import LogMailer

    return LogMailer()


@dataclass
class Env:
    """Everything a service call needs besides the database session. Swapped wholesale in tests."""

    settings: Settings
    clock: Callable[[], datetime]
    classifier: Classifier
    storage: Storage
    gateway: PaymentGateway
    mailer: "Mailer" = field(default_factory=lambda: _log_mailer())

    def now(self) -> datetime:
        return self.clock()
