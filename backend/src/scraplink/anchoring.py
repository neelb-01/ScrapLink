"""Merkle anchoring of the custody record.

Each lot's chain already shows tampering within that lot. An anchor seals every event recorded
since the previous anchor under one Merkle root, so a single 64-character value commits to the
whole platform's record up to that point. Run it daily (the `anchor-custody` job).

First slice: roots are kept in the database and can be re-checked. Publishing each root outside
ScrapLink, which is what stops the operator rewriting history wholesale, comes next.
"""

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import custody
from .env import Env
from .models import CustodyAnchor, CustodyEvent


def merkle_root(leaves: list[str]) -> str:
    """Pairwise SHA-256 up to a single root; an odd node at any level is paired with itself."""
    if not leaves:
        raise ValueError("a Merkle root needs at least one leaf")
    level = [bytes.fromhex(leaf) for leaf in leaves]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [hashlib.sha256(level[i] + level[i + 1]).digest() for i in range(0, len(level), 2)]
    return level[0].hex()


def _leaf(event: CustodyEvent) -> str:
    # Recomputed from the event's contents, not read from its stored hash, so an edit to the
    # payload is caught even if whoever made it also rewrote the stored hash.
    return custody.event_hash(
        lot_id=event.lot_id,
        seq=event.seq,
        event_type=event.event_type,
        payload=event.payload,
        actor_id=event.actor_id,
        recorded_at=event.recorded_at,
        prev_hash=event.prev_hash,
    )


def _events(db: Session, first_id: int, last_id: int | None = None) -> list[CustodyEvent]:
    query = select(CustodyEvent).where(CustodyEvent.id >= first_id).order_by(CustodyEvent.id)
    if last_id is not None:
        query = query.where(CustodyEvent.id <= last_id)
    return list(db.scalars(query))


def anchor_new_events(db: Session, env: Env) -> CustodyAnchor | None:
    """Seal every event since the last anchor. None when there is nothing new.

    Events are taken in id order. A transaction still open while this runs could commit a lower
    id afterwards and fall behind every later anchor; the job runs when trading is quiet, and
    recording each event's anchor on the event itself closes that gap later."""
    last = db.scalars(select(CustodyAnchor).order_by(CustodyAnchor.id.desc()).limit(1)).first()
    events = _events(db, (last.last_event_id + 1) if last else 0)
    if not events:
        return None
    anchor = CustodyAnchor(
        first_event_id=events[0].id,
        last_event_id=events[-1].id,
        event_count=len(events),
        merkle_root=merkle_root([_leaf(e) for e in events]),
        created_at=env.now(),
    )
    db.add(anchor)
    db.flush()
    return anchor


def anchor_holds(db: Session, anchor: CustodyAnchor) -> bool:
    events = _events(db, anchor.first_event_id, anchor.last_event_id)
    if len(events) != anchor.event_count:
        return False
    return merkle_root([_leaf(e) for e in events]) == anchor.merkle_root
