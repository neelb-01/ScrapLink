"""Per-lot append-only SHA-256 hash chain.

Each event commits to its predecessor, so altering, removing or reordering any past event
breaks every hash after it. A certificate records the head hash at issue time; verification
recomputes the chain from genesis and checks that head is still in it.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import CustodyEvent, Lot, User

GENESIS_HASH = "0" * 64


def canonical_json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def event_hash(
    *,
    lot_id: uuid.UUID,
    seq: int,
    event_type: str,
    payload: dict,
    actor_id: uuid.UUID | None,
    recorded_at: str,
    prev_hash: str,
) -> str:
    body = {
        "lot_id": str(lot_id),
        "seq": seq,
        "event_type": event_type,
        "payload": payload,
        "actor_id": str(actor_id) if actor_id else None,
        "recorded_at": recorded_at,
        "prev_hash": prev_hash,
    }
    return hashlib.sha256(canonical_json(body)).hexdigest()


def append_event(
    db: Session, lot: Lot, event_type: str, payload: dict, *, actor: User | None, now: datetime
) -> CustodyEvent:
    last = db.scalars(
        select(CustodyEvent)
        .where(CustodyEvent.lot_id == lot.id)
        .order_by(CustodyEvent.seq.desc())
        .limit(1)
    ).first()
    seq = last.seq + 1 if last else 1
    prev_hash = last.hash if last else GENESIS_HASH
    recorded_at = now.isoformat(timespec="microseconds")
    actor_id = actor.id if actor else None
    event = CustodyEvent(
        lot_id=lot.id,
        seq=seq,
        event_type=event_type,
        payload=payload,
        actor_id=actor_id,
        recorded_at=recorded_at,
        prev_hash=prev_hash,
        hash=event_hash(
            lot_id=lot.id,
            seq=seq,
            event_type=event_type,
            payload=payload,
            actor_id=actor_id,
            recorded_at=recorded_at,
            prev_hash=prev_hash,
        ),
    )
    db.add(event)
    db.flush()
    return event


def lot_events(db: Session, lot_id: uuid.UUID) -> list[CustodyEvent]:
    return list(
        db.scalars(
            select(CustodyEvent).where(CustodyEvent.lot_id == lot_id).order_by(CustodyEvent.seq)
        )
    )


@dataclass(frozen=True)
class ChainCheck:
    valid: bool
    reason: str | None
    head_hash: str
    length: int


def verify_chain(events: list[CustodyEvent]) -> ChainCheck:
    prev_hash = GENESIS_HASH
    for expected_seq, event in enumerate(events, start=1):
        verified = expected_seq - 1
        if event.seq != expected_seq:
            return ChainCheck(False, f"event {expected_seq} is missing", prev_hash, verified)
        if event.prev_hash != prev_hash:
            return ChainCheck(
                False, f"event {event.seq} does not link to its predecessor", prev_hash, verified
            )
        recomputed = event_hash(
            lot_id=event.lot_id,
            seq=event.seq,
            event_type=event.event_type,
            payload=event.payload,
            actor_id=event.actor_id,
            recorded_at=event.recorded_at,
            prev_hash=event.prev_hash,
        )
        if recomputed != event.hash:
            return ChainCheck(
                False, f"event {event.seq} was altered after it was recorded", prev_hash, verified
            )
        prev_hash = event.hash
    return ChainCheck(True, None, prev_hash, len(events))
