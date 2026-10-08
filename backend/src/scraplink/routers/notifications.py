from fastapi import APIRouter
from sqlalchemy import select, update

from ..deps import DB, CurrentUser, EnvDep
from ..errors import NotFound
from ..models import Notification
from ..notifications import unread_count
from ..schemas import NotificationOut, NotificationsOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _out(note: Notification) -> NotificationOut:
    return NotificationOut(
        id=note.id,
        lot_id=note.lot_id,
        kind=note.kind,
        text=note.text,
        created_at=note.created_at,
        read=note.read_at is not None,
        emailed=note.emailed_at is not None,
    )


@router.get("", response_model=NotificationsOut)
def notifications(db: DB, user: CurrentUser, limit: int = 50) -> NotificationsOut:
    """Newest first. The app polls this for the unread count in the top bar."""
    notes = db.scalars(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.id.desc())
        .limit(min(max(limit, 1), 200))
    )
    return NotificationsOut(unread=unread_count(db, user), items=[_out(n) for n in notes])


@router.post("/read", response_model=NotificationsOut)
def mark_all_read(db: DB, env: EnvDep, user: CurrentUser) -> NotificationsOut:
    db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
        .values(read_at=env.now())
    )
    db.commit()
    return notifications(db, user)


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, db: DB, env: EnvDep, user: CurrentUser) -> NotificationOut:
    note = db.get(Notification, notification_id)
    if note is None or note.user_id != user.id:
        raise NotFound("notification not found")
    if note.read_at is None:
        note.read_at = env.now()
        db.commit()
    return _out(note)
