from fastapi import APIRouter
from sqlalchemy import select

from .. import ledger
from ..deps import DB, CurrentUser
from ..models import LedgerAccount, LedgerPosting, LedgerTransaction
from ..schemas import WalletEntryOut, WalletOut

router = APIRouter(tags=["wallet"])


@router.get("/wallet", response_model=WalletOut)
def wallet(db: DB, user: CurrentUser) -> WalletOut:
    account = db.scalars(
        select(LedgerAccount).where(LedgerAccount.key == f"wallet:{user.id}")
    ).first()
    if account is None:
        return WalletOut(balance_paise=0, entries=[])
    rows = db.execute(
        select(
            LedgerTransaction.kind,
            LedgerTransaction.lot_id,
            LedgerPosting.amount_paise,
            LedgerTransaction.created_at,
        )
        .join(LedgerPosting, LedgerPosting.transaction_id == LedgerTransaction.id)
        .where(LedgerPosting.account_id == account.id)
        .order_by(LedgerTransaction.created_at.desc(), LedgerTransaction.id.desc())
    )
    return WalletOut(
        balance_paise=ledger.balance(db, account),
        entries=[
            WalletEntryOut(kind=kind, lot_id=lot_id, amount_paise=amount, created_at=created_at)
            for kind, lot_id, amount, created_at in rows
        ],
    )
