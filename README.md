# SENTINEL SHIELD

<p align="center">
  <strong>Multi-chain Wallet Security Scanner &mdash; 16 EVM Chains</strong>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#api-reference">API Reference</a> &bull;
  <a href="#architecture">Architecture</a> &bull;
  <a href="TESTING.md">Tests</a> &bull;
  <a href="SECURITY.md">Security</a> &bull;
  <a href="CONTRIBUTING.md">Contributing</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Go-1.22-00ADD8?logo=go&logoColor=white" alt="Go 1.22" />
  <img src="https://img.shields.io/badge/Rust-stable-DEA584?logo=rust&logoColor=white" alt="Rust" />
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" alt="Python 3.11" />
  <img src="https://img.shields.io/badge/Solidity-0.8.x-363636?logo=solidity&logoColor=white" alt="Solidity" />
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black" alt="React 18" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License" />
</p>

---

## Overview

SENTINEL scans wallet approvals across **16 mainnet EVM chains**, decompiles contract bytecode, detects 30+ vulnerability patterns, and lets users revoke dangerous approvals — all from a single dashboard.

**Core pipeline:** User wallet &rarr; Go API (concurrent multi-chain RPC) &rarr; Rust decompiler (bytecode &rarr; opcodes) &rarr; Python analyzer (heuristic risk scoring) &rarr; React frontend (actionable results).

---

## Supported Chains

| Ethereum & L2s | Alt L1s |
|:---|:---|
| Ethereum (1) &bull; Arbitrum One (42161) &bull; Optimism (10) &bull; Base (8453) | BNB Chain (56) &bull; Polygon PoS (137) &bull; Avalanche (43114) &bull; Fantom (250) |
| zkSync Era (324) &bull; Linea (59144) &bull; Scroll (534352) &bull; Polygon zkEVM (1101) | Cronos (25) &bull; Gnosis (100) &bull; Celo (42220) &bull; Moonbeam (1284) |

---

## Key Features

| Feature | Description |
|---------|-------------|
| **16-Chain Scanning** | Concurrent RPC calls across all supported mainnets |
| **Bytecode Decompilation** | Rust-powered opcode analysis and control-flow graph generation |
| **30+ Vuln Patterns** | Honeypots, hidden mints, reentrancy, proxy risks, access control flaws |
| **One-click Revoke** | Remove dangerous approvals directly from the dashboard |
| **Risk Scoring** | Per-approval + global wallet health score (0–100) |
| **JWT + API Key Auth** | HS256 JWT tokens with API-key fallback for all protected endpoints |
| **Distributed Rate Limiting** | Redis-backed rate limiter with automatic in-memory fallback |
| **Prometheus Metrics** | `/metrics` endpoint — request counters, latency histograms, business KPIs |
| **PostgreSQL + Redis** | Persistent scan history, distributed caching (optional, graceful degradation) |

---

## Architecture

```
                            ┌──────────────────────────┐
                            │   Frontend (React + TS)  │
                            │   Vite · Tailwind · wagmi│
                            └────────────┬─────────────┘
                                         │ HTTPS
                            ┌────────────▼─────────────┐
                            │      API Server (Go)     │
                            │  JWT · Rate Limit · CORS │
                            │  Prometheus · Middleware  │
                            └──┬─────────┬──────────┬──┘
                               │         │          │
                    ┌──────────▼──┐ ┌────▼────┐ ┌───▼──────────┐
                    │ Decompiler  │ │Analyzer │ │  PostgreSQL  │
                    │   (Rust)    │ │(Python) │ │  + Redis     │
                    │ Opcodes/CFG │ │Heuristic│ │  Cache/Store │
                    └─────────────┘ └─────────┘ └──────────────┘
                               │
                    ┌──────────▼──────────────────────┐
                    │   On-chain Contracts (Sol + Yul)│
                    │ SentinelRegistry · BatchRevokeYul│
                    └─────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Role |
|-------|-----------|------|
| **API** | Go 1.22 | HTTP server, multi-chain RPC, middleware (JWT, rate limit, CORS, metrics) |
| **Decompiler** | Rust (stable) | EVM bytecode disassembly, opcode parsing, CFG generation |
| **Analyzer** | Python 3.11+ | Heuristic vulnerability detection, risk scoring |
| **Frontend** | React 18, TypeScript, Vite, Tailwind, RainbowKit | Dashboard, wallet connection, one-click revoke |
| **Contracts** | Solidity 0.8.x + Yul | On-chain registry, gas-optimized batch revoke |
| **Data** | PostgreSQL 16, Redis 7 | Scan history, distributed cache, rate limiting |
| **Infra** | Docker Compose, GitHub Actions CI/CD | Multi-container deployment, 5-stage pipeline |

---

## Quick Start

### Docker (recommended)

```bash
git clone https://github.com/Faraone-Dev/SENTINEL.git
cd SENTINEL
cp config/.env.example config/.env    # edit with your RPC keys
docker-compose up -d                  # starts all 6 services
```

Services are available at:

| Service | URL |
|---------|-----|
| Frontend | `http://localhost:80` |
| API | `http://localhost:8080` |
| Prometheus metrics | `http://localhost:8080/metrics` |
| Decompiler | `http://localhost:3000` |
| Analyzer | `http://localhost:5000` |

### Manual (development)

```bash
# API Server
cd api && go run cmd/server/main.go          # :8080

# Decompiler
cd decompiler && cargo run -- --server --port 3000   # :3000

# Analyzer
cd analyzer && python src/server.py          # :5000

# Frontend
cd frontend && npm install && npm run dev    # :5173
```

### Makefile shortcuts

```bash
make build          # Build all components
make test           # Run all test suites
make docker-up      # docker-compose up -d
make docker-down    # docker-compose down
make help           # List all targets
```

---

## Configuration

Copy `config/.env.example` to `config/.env` and set:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ALCHEMY_API_KEY` | Recommended | — | Alchemy RPC key for reliable chain access |
| `ETHERSCAN_API_KEY` | Optional | — | Block explorer API (free tier works) |
| `ADMIN_API_KEY` | Production | — | API key for protected endpoints |
| `JWT_SECRET` | Optional | — | HS256 signing key (≥32 chars); enables JWT auth |
| `DATABASE_URL` | Optional | — | PostgreSQL connection string |
| `REDIS_URL` | Optional | — | Redis connection string |
| `RATE_LIMIT_RPM` | Optional | `100` | Max requests per minute per IP |
| `PORT` | Optional | `8080` | API server port |
| `CORS_ORIGINS` | Optional | `*` | Comma-separated allowed origins |

> All infrastructure dependencies (PostgreSQL, Redis) are optional. The server degrades gracefully to in-memory caching and local rate limiting when they're unavailable.

---

## API Reference

### Public Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/health` | None | Health check + version info |
| `GET` | `/metrics` | None | Prometheus-compatible metrics |
| `GET` | `/api/v1/chains` | None | List all 16 supported chains |

### Protected Endpoints (JWT or API Key)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/scan?wallet=0x...&chains=ethereum,base` | Scan wallet approvals across chains |
| `GET` | `/api/v1/analyze?contract=0x...&chain=ethereum` | Deep-analyze a single contract |
| `POST` | `/api/v1/analyze/batch` | Batch analyze up to 10 contracts |
| `POST` | `/api/v1/auth/token` | Issue JWT token (admin API key required) |

### Authentication

**Option A — API Key:**
```bash
curl -H "X-API-Key: YOUR_KEY" http://localhost:8080/api/v1/chains
```

**Option B — JWT Token:**
```bash
# 1. Get token (requires admin API key)
TOKEN=$(curl -s -X POST http://localhost:8080/api/v1/auth/token \
  -H "X-API-Key: ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"sub":"my-app","role":"reader","ttl":"24h"}' | jq -r .token)

# 2. Use token
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/v1/scan?wallet=0x...
```

### Microservices

| Service | Port | Endpoints |
|---------|------|-----------|
| **Decompiler** (Rust) | 3000 | `GET /health` · `POST /analyze` |
| **Analyzer** (Python) | 5000 | `GET /health` · `POST /api/analyze` · `GET /api/stats` |

---

## Observability

### Prometheus Metrics (`GET /metrics`)

| Metric | Type | Description |
|--------|------|-------------|
| `sentinel_http_requests_total` | Counter | Requests by endpoint, method, status |
| `sentinel_http_request_duration_seconds` | Histogram | Latency per endpoint (10ms–10s buckets) |
| `sentinel_scans_total` | Counter | Wallet scans performed |
| `sentinel_analyzes_total` | Counter | Contract analyses performed |
| `sentinel_rate_limit_blocks_total` | Counter | Requests blocked by rate limiter |
| `sentinel_auth_failures_total` | Counter | Failed authentication attempts |
| `sentinel_uptime_seconds` | Gauge | Server uptime |

Scrape config for `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: sentinel-api
    static_configs:
      - targets: ['sentinel-api:8080']
```

---

## Project Structure

```
SENTINEL/
├── api/                          # Go API server
│   ├── cmd/server/
│   │   ├── main.go               # Server, routes, middleware (~2300 lines)
│   │   ├── database.go           # PostgreSQL client
│   │   ├── redis.go              # Redis cache + distributed rate limiting
│   │   ├── metrics.go            # Prometheus metrics (zero dependencies)
│   │   ├── jwt.go                # JWT auth (HS256, zero dependencies)
│   │   ├── *_test.go             # Unit, fuzz, integration, benchmark tests
│   │   └── server.exe            # Compiled binary
│   ├── Dockerfile
│   └── go.mod
├── analyzer/                     # Python risk analyzer
│   ├── src/                      # analyzer.py, server.py
│   ├── tests/
│   └── requirements.txt
├── decompiler/                   # Rust bytecode decompiler
│   ├── src/                      # main.rs, server.rs
│   └── Cargo.toml
├── contracts/                    # Solidity + Yul smart contracts
│   ├── src/                      # SentinelRegistry.sol, BatchRevokeYul
│   ├── test/
│   └── foundry.toml
├── frontend/                     # React dashboard
│   ├── src/
│   │   ├── App.tsx               # Main app (~350 lines)
│   │   ├── components/           # 9 extracted UI components
│   │   └── __tests__/            # 54+ Vitest unit tests
│   └── package.json
├── db/                           # PostgreSQL schema (init.sql)
├── tests/e2e/                    # End-to-end test suite
├── config/                       # .env, .env.example
├── scripts/                      # Build & deploy scripts
├── .github/workflows/ci.yml     # CI/CD pipeline (6 jobs)
├── docker-compose.yml            # Full stack (6 services)
├── Makefile                      # Build, test, Docker shortcuts
├── TESTING.md                    # Test suite documentation
├── SECURITY.md                   # Security policy & bug bounty
└── CONTRIBUTING.md               # Contribution guidelines
```

---

## Vulnerability Detection

| Category | Patterns |
|----------|----------|
| **Token Scams** | Honeypot, hidden mint, hidden fee, blacklist functions |
| **Approval Risks** | Unlimited allowances, unverified spenders, stale approvals |
| **Proxy Risks** | Upgradeable without timelock, recent upgrades, implementation mismatch |
| **Reentrancy** | State changes after external calls, cross-function reentrancy |
| **Access Control** | Single owner, no multisig, centralized kill switches |
| **Flash Loan** | Price oracle manipulation, unchecked callbacks |
| **Logic Bugs** | Integer overflow, unchecked return values, tx.origin auth |

---

## Testing

**~90,000 total test executions** across all components (including fuzz and property-based runs).

| Component | Tests | Type | Runner |
|-----------|-------|------|--------|
| **Go API** | 15,000+ | Unit + Fuzz + Integration + Benchmark | `go test` |
| **Rust Decompiler** | 20,031 | Unit + Fuzz | `cargo test` |
| **Solidity Contracts** | 30,000+ | Foundry fuzz (30k runs) | `forge test` |
| **Python Analyzer** | 12,000+ | Hypothesis property-based | `pytest` |
| **React Frontend** | 54+ unit, 15,000+ fast-check | Vitest + @testing-library | `npx vitest` |
| **E2E** | Suite | API integration tests | `go test ./tests/e2e/` |

See [TESTING.md](TESTING.md) for full details, fuzz configuration, and CI recipes.

---

## CI/CD Pipeline

GitHub Actions runs on every push to `main`/`develop` and on PRs:

| Stage | What it does |
|-------|-------------|
| **Lint** | golangci-lint, `cargo clippy`, `ruff + mypy`, ESLint, `forge fmt` |
| **Test** | All 5 language test suites with coverage thresholds |
| **Build** | Docker images for api, decompiler, analyzer, frontend (GHCR) |
| **E2E** | Integration tests against Redis + PostgreSQL services |
| **Security** | `gosec`, `cargo-audit`, `safety`, Slither (smart contracts) |
| **Deploy** | Contract deployment (on release) + service deployment (on main push) |

---

## Security

- Rate limiting per IP (Redis distributed + in-memory fallback)
- JWT (HS256) + API key dual authentication
- CORS with configurable origins
- Security headers (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection)
- Request body size limits (1 MB)
- Graceful shutdown with 10s drain timeout
- Bug bounty program — see [SECURITY.md](SECURITY.md)

---

## License

[MIT](LICENSE)

---

<p align="center">
  <strong>Faraone-Dev</strong> &mdash; <a href="https://github.com/Faraone-Dev">@Faraone-Dev</a><br/>
  Go · Rust · Python · Solidity · Yul · TypeScript
</p>

<p align="center"><em>"Defense built by those who understand offense."</em></p>
