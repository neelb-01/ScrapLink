"""Double-entry ledger. Every movement of money is a balanced transaction recorded here first;
the payment rail only confirms what the ledger already expects.
"""

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import LedgerAccount, LedgerPosting, LedgerTransaction


def _account(db: Session, key: str, kind: str, **owner) -> LedgerAccount:
    account = db.scalars(select(LedgerAccount).where(LedgerAccount.key == key)).first()
    if account is None:
        account = LedgerAccount(key=key, kind=kind, **owner)
        db.add(account)
        db.flush()
    return account


def gateway_account(db: Session) -> LedgerAccount:
    """Money that entered from the payment rail. Its balance is the negative of funds held."""
    return _account(db, "gateway:inbound", "gateway")


def escrow_account(db: Session, lot_id: uuid.UUID) -> LedgerAccount:
    return _account(db, f"escrow:{lot_id}", "escrow", lot_id=lot_id)


def wallet_account(db: Session, user_id: uuid.UUID) -> LedgerAccount:
    return _account(db, f"wallet:{user_id}", "wallet", user_id=user_id)


def post_transaction(
    db: Session,
    *,
    kind: str,
    idempotency_key: str,
    lot_id: uuid.UUID | None,
    now: datetime,
    postings: list[tuple[LedgerAccount, int]],
) -> LedgerTransaction:
    existing = db.scalars(
        select(LedgerTransaction).where(LedgerTransaction.idempotency_key == idempotency_key)
    ).first()
    if existing is not None:
        return existing
    if sum(amount for _, amount in postings) != 0:
        raise ValueError(f"unbalanced ledger transaction {idempotency_key}")

    txn = LedgerTransaction(
        kind=kind, idempotency_key=idempotency_key, lot_id=lot_id, created_at=now
    )
    db.add(txn)
    db.flush()
    for account, amount in postings:
        if amount:
            db.add(LedgerPosting(transaction_id=txn.id, account_id=account.id, amount_paise=amount))
    db.flush()
    return txn


def balance(db: Session, account: LedgerAccount) -> int:
    # PostgreSQL's SUM(bigint) is NUMERIC, which arrives as Decimal; money stays int here.
    return int(
        db.scalar(
            select(func.coalesce(func.sum(LedgerPosting.amount_paise), 0)).where(
                LedgerPosting.account_id == account.id
            )
        )
    )
