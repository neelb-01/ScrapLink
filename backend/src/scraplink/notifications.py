"""Notifications: in the app always, and by email when the person gave an address.

First slice: a notification row is written in the same transaction as the event it reports
(a bid, an award, a payment, a pickup, a weighbridge reading, a settlement, a KYC decision).
The email goes out straight away through `env.mailer`, which logs instead of sending until
SMTP_HOST is set. A failed email never fails the trade. Queued sending with retries, SMS and
WhatsApp come later.
"""

import logging
import smtplib
from collections import deque
from email.message import EmailMessage
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import Settings
from .models import Lot, Notification, User

log = logging.getLogger(__name__)


class Mailer(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


class LogMailer:
    """Development default: each email is logged, and the last few kept for tests."""

    def __init__(self) -> None:
        self.sent: deque[tuple[str, str, str]] = deque(maxlen=100)

    def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append((to, subject, body))
        log.info("email to %s: %s", to, subject)


class SmtpMailer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send(self, to: str, subject: str, body: str) -> None:
        s = self.settings
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = s.smtp_from, to, subject
        message.set_content(body)
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if s.smtp_username:
                smtp.login(s.smtp_username, s.smtp_password)
            smtp.send_message(message)


def rupees(paise: int) -> str:
    return f"₹{paise // 100:,}" + (f".{paise % 100:02d}" if paise % 100 else "")


def kilos(grams: int) -> str:
    whole, part = divmod(grams, 1000)
    return f"{whole:,}" + (f".{part:03d}".rstrip("0") if part else "") + " kg"


def mailer_from_settings(settings: Settings) -> Mailer:
    return SmtpMailer(settings) if settings.smtp_host else LogMailer()


def notify(
    db: Session, env, user: User, text: str, *, kind: str, lot: Lot | None = None
) -> Notification:
    note = Notification(
        user_id=user.id,
        lot_id=lot.id if lot else None,
        kind=kind,
        text=text[:300],
        created_at=env.now(),
    )
    db.add(note)
    if user.email:
        link = (
            f"{env.settings.public_base_url}/lots/{lot.id}" if lot else env.settings.public_base_url
        )
        try:
            env.mailer.send(user.email, f"ScrapLink: {text[:80]}", f"{text}\n\n{link}\n")
            note.emailed_at = env.now()
        except Exception:
            log.exception("could not email notification %s to %s", kind, user.email)
    return note


def unread_count(db: Session, user: User) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
    )
