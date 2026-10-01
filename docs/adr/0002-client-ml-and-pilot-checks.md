# ADR 0002: Web client, ML service, and pilot-readiness checks

**Status:** accepted · **Date:** 2026-10-01 · **Builds on:** [ADR 0001](0001-first-slice.md)

## Context

After ADR 0001 the trade path existed only as an API. The 10% slice also promised a phone-first
client (three-screen capture, assisted capture), an off-the-shelf classifier, and confidence
that the code runs on the target database and payment rail.

## Decisions

### Web client (`web/`)

- **React + TypeScript + Vite, no UI kit.** About 94 KB of JS gzipped, for low-end Android
  on slow connections.
- **Types are generated from the backend's OpenAPI schema** (`npm run gen:api`), so if a
  backend change breaks the client, `npm run build` fails before any browser sees it.
- **Each role lands where its work is.** Sellers and agents go to their lots, buyers to the
  market, admins to the approvals queue. Navigation is three items in a 60px bottom bar.
- **Capture takes three screens** (photo → what is it → price and bidding window).
  Photos are shrunk on the phone to 1600px JPEG before upload. Agents find the seller by
  phone number (`GET /sellers/lookup`).
- **Plain words, not system states.** Each lot status is phrased for the person viewing it
  ("You won. Pay to confirm", "Weighed. Check the reading"), and the custody record reads as a
  timeline of what happened.
- **Visual identity comes from the scrap yard.** Each lot is drawn as a cut metal tag in the
  colour of its metal. Actions are safety-yellow raised keys. Type is Archivo, with its wide
  cut used for weights and rupees. The page stays light and high-contrast for use in sunlight.
- **The definition of done is a browser test** (`web/e2e/trade.spec.ts`). Three separate
  sessions (admin, seller, buyer) take one lot from registration to a verified certificate in
  the installed Chrome. The test server (`backend/scripts/e2e_server.py`) adds a clock-advance
  route so a one-day auction closes instantly. That route exists only in the test script.

### ML service (`ml/`)

- **Zero-shot CLIP ViT-B/32** with prompt-ensembled text descriptions per metal, plus an
  `other` class so non-metal photos come back with low confidence. There's no grade: judging
  contamination zero-shot isn't credible.
- **A sanity check found it overconfident** (details in `ml/README.md`). Of 18 real photos, 16
  fell below the 0.75 prefill threshold, and of the 2 above it, one was wrong: cardboard called
  aluminium at 0.83. The design already contains this: the seller always confirms, and the
  weighbridge settles. A fine-tuned model replaces it once pilot photos are labelled, and the
  backend already records each photo with the seller's confirmed metal.

### Pilot-readiness checks

- **PostgreSQL 16.11** (portable binaries, no Docker). The Alembic migration applies with no
  drift, and all 40 backend tests pass against it. The run found a real bug: `SUM()` over a
  `BIGINT` column comes back as `NUMERIC`, which psycopg returns as `Decimal`, and that broke
  settlement. Ledger balances are now forced to `int`. SQLite never showed this.
- **Razorpay Checkout callback** (`POST /payments/razorpay/verify`). It checks the
  `order_id|payment_id` HMAC with the key secret, so a sandbox run doesn't need a public
  webhook URL. The webhook stays as the reconciliation path, and capture is idempotent across
  both. **Not yet run against the Razorpay sandbox:** that needs test-mode keys.
- **HTTP clients are pooled.** Making a new `httpx` client per call cost about 0.3 s, and
  `localhost` on Windows added about 2 s through an IPv6 fallback. Classification went from
  3.1 s to 0.07 s per photo.

## Consequences

- Done: the slice is usable by people, not only through the API.
- Still open before a pilot: a Razorpay sandbox run with real test keys, a way to resolve
  disputes, a funding deadline with re-award to the runner-up, Malayalam (interface strings and
  a Unicode certificate font), and payouts from the wallet to a bank account.
- The ML service should run with a higher threshold, or as a hint only, until fine-tuned.
