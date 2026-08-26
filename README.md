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

**Pre-implementation.** This repository currently contains requirements and initialisation only — no application code yet.

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

Architecture decision records land in `docs/` next.

## Design constraints that are not negotiable

- **AI grading is confidence-aware and human-verified, never fully automated.** Published accuracy on cluttered waste imagery sits around 61% F1; the system treats a model output as an assisted estimate subject to confidence thresholds and seller confirmation, with weighbridge and buyer inspection downstream.
- **Adoption is an architecture constraint, not polish.** A comparable deployed system recorded 46.2% non-adoption driven by interface depth, typography, device capability and digital literacy — not technical deficiency. Assisted capture, shallow navigation, offline tolerance on low-end Android, and immediate commercial payoff are requirements.
- **Compliance rules live in the matching engine.** E-waste and battery lots match only counterparties holding valid authorisations, so a non-compliant match is impossible rather than discouraged.

## Development

Copy [`.env.example`](.env.example) to `.env` and fill it in. Real secrets never leave your machine.

Build, lint and test commands will be added here once the service skeleton exists.
