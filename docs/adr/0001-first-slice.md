# ADR 0001 — The first slice: one verified, valued, settled trade

**Status:** accepted · **Date:** 2026-10-01

## Context

The research gap analysis puts ScrapLink's novelty in the *integration*, and specifically in the
verification, valuation and settlement layer that existing marketplaces (Upvalue, Paper 12) stop
short of. Dynamic pricing and payments/escrow are the two rows no reviewed system fills.

So the first slice can't be a subset of features built to completion. A horizontal slice (say
classification, listings and search) would rebuild a listing board. It has to be a vertical
slice: one path through the whole pipeline, as thin as possible, that still reaches pricing
and escrow.

## Decision

Build one trade path end to end, for **metal scrap only** (steel HMS, cast iron, copper, brass,
aluminium), in the backend first.

```
photo → suggested category (confidence-gated) → seller confirms category, grade, weight
      → rules-based price range → sealed-bid auction → escrow funded
      → pickup → weighbridge weight + slip photo → seller accepts
      → settlement on measured weight → hash-chained certificate
```

Metals are priced by weight, have public reference prices, differ visibly between grades, and
make up most of the Kerala scrap network described in Paper 17.

### Choices inside the slice

| Concern | Decision | Why |
|---|---|---|
| AI classification | The backend calls a separate ML service (`classification.py` documents the contract). A suggestion is prefilled only at ≥ 0.75 confidence and for a known material. The seller always confirms. If the service is down, capture still works by hand. | Paper 13: realistic cluttered-waste accuracy is ~61% F1. The model assists and never decides. |
| Grade | A / B / C with multipliers 1.00 / 0.85 / 0.65 | Explainable to a low-literacy seller. It becomes contamination estimation later. |
| Pricing | Admin-set reference rate × grade multiplier × weight, shown as ±10% | Transparent (Paper 18: suppliers capture ~10% of value). Learned prediction can replace `pricing.estimate` without changing its callers. |
| Auction | Sealed bids **per kg**. Highest wins, ties go to the earliest (a revised bid re-queues). Optional reserve. Closes lazily on access, plus a `close-auctions` command for cron. | Bidding per kg lets settlement follow the weighbridge, not the declaration. There's no Redis dependency yet. |
| Escrow | Winning rate × declared weight × 1.10, rounded up. Settles at rate × **measured** weight, and the rest is refunded. Above the tolerance, settlement is blocked (`disputed`). | This is the moment that proves the listed lot is the lot that arrived. |
| Ledger | Double-entry, integer paise, balanced transactions with idempotency keys. Money is recorded in the ledger before the payment rail is involved. | Webhooks retry, and every movement of money has to balance. |
| Payment rail | `simulated` for development and demos. Razorpay orders and signed webhooks are built for the pilot. | The real rail is sandbox-only during the pilot anyway. |
| Custody | One SHA-256 hash chain per lot. Each state change appends an event in the same DB transaction. The certificate stores the head hash, and public `/verify` recomputes the chain. | Tamper-evident without a blockchain. The daily Merkle anchor across lots comes later. |
| KYC | GSTIN format + checksum and PAN format checks, then admin approval. Buyers must give a GSTIN. | This catches typos and made-up numbers. A live GSTN lookup comes later. |
| Assisted capture | An `agent` role can create and confirm lots for an approved seller | Paper 16: 46.2% non-adoption came from interface and literacy, not technology. |
| Identity | Phone number and password | Phones are universal among the target users and email isn't. OTP comes later. |
| Database | Written for PostgreSQL, and runs on SQLite for local development and tests. Timestamps go through a `UTCDateTime` type so both behave the same. | There was no Postgres or Docker on the development machine. The schema is portable, and Alembic manages it. |
| Units | Money in integer paise, weight in integer grams, everywhere | No floats in the trade path. |

### Explicitly out of the slice

RFQ, spot/long-term contracts, route optimisation and logistics partners, weighbridge hardware
(Phase 3), wallet payouts to bank accounts, invoicing/GST, dispute resolution workflow, deadline
for the winner to fund, refresh tokens/OTP, S3 storage, ESG analytics, Merkle anchoring, the
ML service itself, and the web/mobile clients.

## Consequences

- The backend demonstrates the whole contribution in miniature. `tests/test_trade_flow.py` is
  the definition of done: photo to certificate, escrow reconciled to the weighbridge, and an
  altered past event makes verification fail.
- A disputed lot has no resolution path yet. Admins will need one before the pilot.
- If the winner never funds, the lot stays `awarded`. A funding deadline with re-award to the
  runner-up is the next rule to add.
- Certificates use built-in PDF fonts (Latin-1). Malayalam and other Indic names need an
  embedded Unicode font before the pilot.
