"""Pure-logic checks for the pieces money and evidence depend on."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from scraplink import custody, ledger, pricing
from scraplink.kyc import gstin_check_char, normalise_gstin, normalise_pan
from scraplink.models import Lot, LotStatus, User
from scraplink.security import hash_password, verify_password

NOW = datetime(2026, 10, 1, tzinfo=UTC)


@pytest.mark.parametrize("gstin", ["27AAPFU0939F1ZV", "29AAGCB7383J1Z4"])
def test_published_gstins_pass_checksum(gstin):
    assert gstin_check_char(gstin[:14]) == gstin[14]
    assert normalise_gstin(f"  {gstin.lower()} ") == gstin


def test_malformed_identifiers_are_rejected():
    with pytest.raises(ValueError):
        normalise_gstin("27AAPFU0939F1ZX")
    with pytest.raises(ValueError):
        normalise_gstin("27AAPFU0939F1Z")
    with pytest.raises(ValueError):
        normalise_pan("AAPFU09391")


def test_amounts_round_half_up_to_the_paisa():
    assert pricing.amount_for(57_800, 250_000) == 14_450_000
    assert pricing.amount_for(333, 1_500) == 500  # 499.5 rounds up
    assert pricing.amount_for(333, 1_498) == 499  # 498.834


def test_estimate_and_band():
    est = pricing.estimate(3_200, "C", 1_000_000, Decimal("0.10"))
    assert est.rate_paise_per_kg == 2_080  # 0.65 x 32.00
    assert est.total_paise == 2_080_000
    assert (est.low_paise, est.high_paise) == (1_872_000, 2_288_000)


def test_escrow_rounds_up_so_the_tolerance_is_always_covered():
    amount = pricing.escrow_amount(333, 1_001, Decimal("0.10"))
    assert amount == 367  # 366.6663 rounds up, never down
    assert amount >= pricing.amount_for(333, 1_101)


def test_password_hashing():
    stored = hash_password("s3cret-passphrase")
    assert verify_password("s3cret-passphrase", stored)
    assert not verify_password("wrong", stored)
    assert not verify_password("anything", "not-a-hash")


def _lot(db) -> Lot:
    user = User(phone="9000000000", name="u", password_hash="x", role="seller", created_at=NOW)
    db.add(user)
    db.flush()
    lot = Lot(
        seller_id=user.id,
        created_by_id=user.id,
        status=LotStatus.DRAFT,
        created_at=NOW,
        photo_key="k",
        photo_sha256="0" * 64,
    )
    db.add(lot)
    db.flush()
    return lot


def test_chain_links_and_detects_each_kind_of_tampering(db):
    lot = _lot(db)
    for n in range(4):
        custody.append_event(db, lot, f"step.{n}", {"n": n}, actor=None, now=NOW)
    events = custody.lot_events(db, lot.id)
    assert events[0].prev_hash == custody.GENESIS_HASH
    assert all(b.prev_hash == a.hash for a, b in zip(events, events[1:], strict=False))
    assert custody.verify_chain(events).valid

    altered = list(events)
    altered[2].payload = {"n": 99}
    assert custody.verify_chain(altered).reason == "event 3 was altered after it was recorded"
    altered[2].payload = {"n": 2}

    assert custody.verify_chain(events[:1] + events[2:]).reason == "event 2 is missing"
    swapped = [events[0], events[2], events[1], events[3]]
    assert not custody.verify_chain(swapped).valid


def test_ledger_rejects_unbalanced_and_ignores_replays(db):
    lot = _lot(db)
    gateway, escrow = ledger.gateway_account(db), ledger.escrow_account(db, lot.id)
    with pytest.raises(ValueError):
        ledger.post_transaction(
            db,
            kind="x",
            idempotency_key="bad",
            lot_id=lot.id,
            now=NOW,
            postings=[(gateway, -100), (escrow, 99)],
        )
    for _ in range(2):
        ledger.post_transaction(
            db,
            kind="x",
            idempotency_key="once",
            lot_id=lot.id,
            now=NOW,
            postings=[(gateway, -100), (escrow, 100)],
        )
    assert ledger.balance(db, escrow) == 100
    assert ledger.balance(db, ledger.wallet_account(db, lot.seller_id)) == 0
