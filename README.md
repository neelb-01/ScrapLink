# ScrapLink

A digital B2B waste-economy platform for industrial recyclable materials.

Digital waste marketplaces already exist — Upvalue and other national platforms operate today as regulated listing and matchmaking boards, where a trade is initiated inside the platform and completed outside it. ScrapLink's contribution is the layer those platforms stop short of: **verification, valuation and settlement**. A lot is independently classified and graded rather than self-declared, carries a predicted price and clears through competitive bidding rather than private negotiation, is fulfilled and weighbridge-confirmed rather than referred to an external partner, and settles inside the platform against a tamper-evident record proving the lot that was advertised is the lot that arrived.

## Pipeline

```
Image → Waste Category → Grade/Purity → Estimated Value → Marketplace → Buyer/Recycler → Logistics → Payment → Certification
```

Organised into four layers:

- **Marketplace / transaction** — RFQ, competitive bidding, spot trades, long-term supply agreements
- **Commercial** — dynamic pricing, digital wallet, invoicing, escrow
- **Operational** — pickup scheduling, logistics partners, route optimisation, weighbridge verification
- **Compliance** — KYC, certification, chain-of-custody, audit-ready records

## Status

**First slice built: the 10%.** One metal-scrap trade runs end to end in a phone-first web client: photo, confidence-gated metal suggestion, seller confirmation, rules-based price range, sealed-bid auction, escrow, pickup, weighbridge reading, settlement on the measured weight, and a hash-chained certificate that anyone can verify. A browser test drives that whole trade with three people (admin, seller, buyer). Scope and trade-offs are in [ADR 0001](docs/adr/0001-first-slice.md), [ADR 0002](docs/adr/0002-client-ml-and-pilot-checks.md) and [ADR 0003](docs/adr/0003-remove-field-agent-role.md).

[`Research Gap Analysis.md`](Research%20Gap%20Analysis.md) is the requirements source: a review of twenty papers whose consolidated comparison tables define the target scope. Every capability marked ✓ in the ScrapLink column is in scope for the delivered system. IoT / real-time waste monitoring (smart bins, weighbridge hardware) is marked P and deferred to Phase 3.

Two rows in those tables are empty for *every* system reviewed, including the operational marketplaces: **dynamic pricing** and **digital payments / escrow**. Those are the contribution, not features among fourteen.

## Planned stack

| Layer | Choice |
|---|---|
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2.0 · Alembic |
| Database | PostgreSQL 16 + PostGIS |
| Async work | Redis + arq (route optimisation, custody anchoring, webhook reconciliation) |
| ML | Separate inference service — classification, grade/purity estimation, price prediction |
| Web portal | React + TypeScript + Vite — buyers, recyclers, admins |
| Mobile | React Native + Expo — generators and dealers, Android-first, offline-first |
| Traceability | Append-only SHA-256 hash chain in PostgreSQL, daily Merkle anchor |
| Payments | Ledger-first escrow; Razorpay Route as the rail (sandbox during the pilot) |
| Market | India — GSTIN/PAN KYC, CPCB/PCB compliance vocabulary |

Architecture decision records live in [`docs/adr/`](docs/adr/).

## Design constraints that are not negotiable

- **AI grading is confidence-aware and human-verified, never fully automated.** Published accuracy on cluttered waste imagery sits around 61% F1; the system treats a model output as an assisted estimate subject to confidence thresholds and seller confirmation, with weighbridge and buyer inspection downstream.
- **Adoption is an architecture constraint, not polish.** A comparable deployed system recorded 46.2% non-adoption driven by interface depth, typography, device capability and digital literacy — not technical deficiency. Assisted capture, shallow navigation, offline tolerance on low-end Android, and immediate commercial payoff are requirements.
- **Compliance rules live in the matching engine.** E-waste and battery lots match only counterparties holding valid authorisations, so a non-compliant match is impossible rather than discouraged.

## Development

| Part | Directory | What it is |
|---|---|---|
| API | [`backend/`](backend/) | FastAPI, SQLAlchemy, Alembic. The trade rules, ledger and custody chain. |
| Web client | [`web/`](web/) | React and TypeScript (Vite), phone-first, for sellers, buyers and admins |
| ML service | [`ml/`](ml/) | Zero-shot metal suggestion from a photo. Read [its README](ml/README.md) before relying on it. |

Copy [`.env.example`](.env.example) to `.env` and fill it in. Real secrets never leave your machine. Set at least `JWT_SECRET`. For local work without PostgreSQL, set `DATABASE_URL=sqlite:///./scraplink-dev.db`.

**Backend** (from `backend/`):

```sh
python -m venv .venv                  # then activate it
pip install -e ".[dev]"               # add ,postgres for PostgreSQL

alembic upgrade head                  # create or upgrade the schema
python -m scraplink.cli seed          # metal-scrap catalogue (illustrative rates)
python -m scraplink.cli create-admin --phone 9999900000 --name Admin
uvicorn scraplink.app:create_app --factory --reload    # API docs at http://localhost:8000/docs

pytest                                # tests (TEST_DATABASE_URL=postgresql+psycopg://... for Postgres)
ruff check . && ruff format --check . # lint
python scripts/demo_trade.py --pdf certificate.pdf     # one full trade, narrated
```

Auctions also close lazily whenever a lot is read. Run `python -m scraplink.cli close-auctions` from cron to close them on time.

**Web client** (from `web/`, with the backend running on port 8000):

```sh
npm install
npm run dev                           # http://localhost:5173, API proxied under /api
npm run build                         # typecheck and production build
npm run gen:api                       # regenerate API types after changing the backend
npx playwright test                   # full trade in Chrome; starts its own servers
```

**ML service** (from `ml/`): see [ml/README.md](ml/README.md). Set `ML_SERVICE_URL=http://127.0.0.1:8001` in `.env` to use it. Leave it empty and sellers choose the metal by hand.
