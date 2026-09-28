# RWA Fractionalization Ledger

FastAPI + PostgreSQL engine for real-world asset fractionalization, concurrent-safe token minting, rental yield distribution, AI document onboarding, and a live Streamlit audit dashboard.

## Features

| Phase | Capability |
|-------|------------|
| 1 | `/mint-fractions` with `SELECT FOR UPDATE` so distributed tokens never exceed the property pool under concurrency |
| 2 | `/distribute-yield` batch payouts using `decimal.Decimal` + platform fee |
| 3 | `/onboard-property-document` LLM (or regex fallback) structured extraction |
| 4 | `app_dashboard.py` Admin + Investor tabs |

## Quick start

### 1. Start PostgreSQL

```bash
docker compose up -d
```

### 2. Configure environment

```bash
copy .env.example .env
```

Optional: set `OPENAI_API_KEY` for LLM document parsing. Without it, the regex fallback extractor is used.

### 3. Install & run API

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

OpenAPI docs: http://127.0.0.1:8000/docs

### 4. Run dashboard

```bash
streamlit run app_dashboard.py

```

## Core models

- **Property** — `id`, `total_value`, `total_tokens`, plus onboarding metadata (`address`, rent, landlord, lease expiry) and `tokens_minted` pool counter
- **TokenLedger** — `id`, `property_id`, `owner_wallet`, `token_balance`, `purchase_timestamp`
- **LedgerTransaction** — immutable audit trail for `mint`, `yield_payout`, and `fee`

## Key endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/properties` | Manually create a property |
| `POST` | `/mint-fractions` | Mint tokens to a wallet (row-locked) |
| `POST` | `/distribute-yield` | Split rental income by ownership stake |
| `POST` | `/onboard-property-document` | Parse deed/lease text and create property |
| `GET` | `/investors/{wallet}/summary` | Holdings + yield + searchable ledger |
| `GET` | `/health` | Liveness check |

## Concurrency safety

`mint_fractions` locks the property row (`WITH FOR UPDATE`) before checking `tokens_minted + request <= total_tokens`, then updates the pool and ledger in the same transaction. Concurrent mint requests serialize on that row so the pool cannot be over-allocated.

## Yield math

```
platform_fee      = rental_income × PLATFORM_FEE_PERCENT / 100
distributable     = rental_income − platform_fee
ownership         = holder.token_balance / property.tokens_minted
net_payout        = distributable × ownership   (last holder absorbs residual cents)
```

All money math uses `Decimal` with `ROUND_HALF_UP` to two places.
