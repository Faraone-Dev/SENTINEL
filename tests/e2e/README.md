# SENTINEL SHIELD - E2E Integration Tests

## Quick Start

```bash
# From project root
chmod +x tests/e2e/run_e2e.sh
./tests/e2e/run_e2e.sh
```

## What it tests

| # | Test | Endpoint |
|---|------|----------|
| 1 | Health checks | All 4 services `/health` |
| 2 | API stats | `GET /api/v1/stats` |
| 3 | Input validation | Scan with missing/bad wallet → 400 |
| 4 | Wallet scan | `GET /api/v1/scan?wallet=...` → 200 + JSON |
| 5 | Contract analysis | `GET /api/v1/analyze?contract=...` → 200 + JSON |
| 6 | Frontend SPA | Serves HTML with "sentinel" |
| 7 | DB connectivity | Via API stats endpoint |
| 8 | CORS headers | `Access-Control` header check |

## CI Integration

```yaml
# GitHub Actions example
e2e:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: chmod +x tests/e2e/run_e2e.sh
    - run: CI=true ./tests/e2e/run_e2e.sh
      env:
        ALCHEMY_API_KEY: ${{ secrets.ALCHEMY_API_KEY }}
        ETHERSCAN_API_KEY: ${{ secrets.ETHERSCAN_API_KEY }}
```

## Requirements

- Docker & Docker Compose v2
- ~2 GB RAM (all services)
- Network access for RPC calls (scan/analyze tests)
