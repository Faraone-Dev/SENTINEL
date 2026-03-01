# 🛡️ SENTINEL SHIELD

**Multi-chain Wallet Security Scanner - 16 EVM Chains**

Real-time protection for your crypto assets. Scan your wallet across **16 mainnet chains**, detect scams, revoke dangerous approvals, and protect your funds.

---

## 🌐 Supported Chains (16 Mainnets)

### Ethereum L2s
| Chain | Icon | Chain ID |
|-------|------|----------|
| Ethereum | ⟠ | 1 |
| Arbitrum One | 🔵 | 42161 |
| Optimism | 🔴 | 10 |
| Base | 🔷 | 8453 |
| zkSync Era | ⚡ | 324 |
| Linea | 📐 | 59144 |
| Scroll | 📜 | 534352 |
| Polygon zkEVM | 🔐 | 1101 |

### Alt L1s
| Chain | Icon | Chain ID |
|-------|------|----------|
| BNB Chain | ⬡ | 56 |
| Polygon PoS | ⬢ | 137 |
| Avalanche C-Chain | 🔺 | 43114 |
| Fantom Opera | 👻 | 250 |
| Cronos | 🌙 | 25 |
| Gnosis Chain | 🦉 | 100 |
| Celo | 🌿 | 42220 |
| Moonbeam | 🌙 | 1284 |

---

## 🔥 Features

- **16-Chain Support**: All major EVM chains with real RPC connections
- **Deep Analysis**: Bytecode decompilation, pattern detection, vulnerability scanning
- **Contract Analysis**: Decompile any contract and detect 30+ vulnerability patterns
- **One-click Revoke**: Remove dangerous approvals directly from the dashboard
- **Real-time Alerts**: Get notified when contracts you approved get upgraded or flagged
- **Risk Scoring**: Global wallet health score based on all interactions

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      SENTINEL SHIELD                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              FRONTEND (React + TypeScript)               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            │                                     │
│                            ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    API SERVER (Go)                       │    │
│  │        Fast, concurrent, multi-chain RPC handling        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            │                                     │
│         ┌──────────────────┼──────────────────┐                 │
│         ▼                  ▼                  ▼                 │
│  ┌────────────┐    ┌────────────────┐   ┌──────────────┐       │
│  │ DECOMPILER │    │ RISK ANALYZER  │   │   DATABASE   │       │
│  │   (Rust)   │    │   (Python)     │   │  (Postgres)  │       │
│  │            │    │  Heuristic     │   │              │       │
│  └────────────┘    └────────────────┘   └──────────────┘       │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │            ON-CHAIN CONTRACTS (Solidity + Yul)           │    │
│  │         Gas-optimized registry and revoke helpers        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Component | Language | Purpose |
|-----------|----------|---------|
| **API Server** | Go | High-performance multi-chain RPC, concurrent scanning |
| **Decompiler** | Rust | Bytecode analysis, opcode parsing, CFG generation |
| **Analyzer** | Python | Heuristic pattern detection, risk scoring |
| **Frontend** | React + TypeScript | User dashboard, wallet connection |
| **Contracts** | Solidity + Yul | On-chain helpers, gas-optimized operations |
| **Database** | PostgreSQL | Vulnerability patterns, scan history |

---

## ✅ Prerequisites

- Go 1.22+
- Rust (stable)
- Python 3.11+
- Node.js 20+
- Docker + Docker Compose (optional)
- Foundry (for contracts testing)

---

## 🔐 Configuration

Copy the environment template and set your API keys:

- [config/.env.example](config/.env.example) → [config/.env](config/.env)

Required/optional environment variables:

- `ALCHEMY_API_KEY` (recommended)
- `ETHERSCAN_API_KEY` (optional; free tier has limits)
- `DECOMPILER_URL` (default: http://localhost:3000)
- `ANALYZER_URL` (default: http://localhost:5000)
- `PORT` (API server, default: 8080)
- `VITE_API_URL` (frontend, default: http://localhost:8080)

---

## 📁 Project Structure

```
SENTINEL/
├── api/                    # Go API server
│   ├── cmd/server/main.go
│   ├── Dockerfile
│   ├── go.mod
│   └── go.sum
├── analyzer/               # Python risk analyzer
│   ├── src/analyzer.py
│   ├── src/server.py
│   ├── tests/
│   └── requirements.txt
├── decompiler/             # Rust bytecode analyzer
│   ├── src/main.rs
│   ├── src/server.rs
│   └── Cargo.toml
├── contracts/              # Solidity + Yul
│   ├── src/SentinelRegistry.sol
│   ├── test/
│   └── foundry.toml
├── frontend/               # React dashboard
│   ├── src/App.tsx
│   └── package.json
├── config/                 # Environment config
│   ├── .env
│   └── .env.example
├── docker-compose.yml
├── Makefile
└── docs/
```

---

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/conditional-team/sentinel.git
cd sentinel

# Configure environment
cp config/.env.example config/.env

# Start all services with Docker
docker-compose up -d

# Or run individually:

# API Server (Go)
cd api && go run cmd/server/main.go
# Runs on http://localhost:8080

# Decompiler (Rust) - Server mode
cd decompiler && cargo run -- --server --port 3000
# Runs on http://localhost:3000

# Analyzer (Python) - Server mode  
cd analyzer && py -3.11 src/server.py
# Runs on http://localhost:5000

# Frontend (React)
cd frontend && npm install && npm run dev
# Runs on http://localhost:5173
```

---

## 📡 API Endpoints

### Go API (Port 8080)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/scan?wallet=0x...&chains=ethereum,polygon` | Scan wallet approvals |
| `GET` | `/api/v1/analyze?contract=0x...&chain=ethereum` | Analyze single contract |
| `POST` | `/api/v1/analyze/batch` | Batch analyze contracts |
| `GET` | `/api/v1/chains` | List supported chains |

### Rust Decompiler (Port 3000)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/analyze` | Analyze bytecode |

### Python Analyzer (Port 5000)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/analyze` | Analyze contract for vulnerabilities |
| `GET` | `/api/stats` | Get analyzer statistics |

---

## 🔍 How It Works

1. **User enters wallet address**
2. **Go API** fetches all interactions across 16 chains (rate-limited)
3. **Rust Decompiler** analyzes bytecode of each contract
4. **Python Analyzer** matches patterns, calculates risk scores
5. **Frontend** displays results with actionable recommendations

---

## ⚡ Vulnerability Detection

| Category | Patterns Detected |
|----------|-------------------|
| **Token Scams** | Honeypot, hidden mint, hidden fee, blacklist |
| **Approval Risks** | Unlimited approvals, malicious spenders |
| **Proxy Risks** | Upgradeable without timelock, recent upgrades |
| **Reentrancy** | State changes after external calls |
| **Access Control** | Single owner, no multisig, centralization |
| **Flash Loan** | Vulnerable to price manipulation |

---

## 📜 License

MIT License - Use freely, contribute back.

---

## 🧪 Testing

**Total Test Executions: ~90,000** (including fuzz and property-based runs)

| Component | Tests | Type |
|-----------|-------|------|
| **Rust Decompiler** | 20,031 | Unit + Fuzz |
| **Solidity Contracts** | 30,000+ | Foundry fuzz (30k runs) |
| **Go API** | 15,000+ | Unit + Fuzz |
| **Python Analyzer** | 12,000+ | Hypothesis property-based |
| **React Frontend** | 15,000+ | Vitest + fast-check |

See [TESTING.md](TESTING.md) for suite details, fuzz configuration, and CI recipes.

---

## 👤 Author

**SENTINEL Team** - Blockchain Security Engineer
- GitHub: [@conditional-team](https://github.com/conditional-team)
- Built with: Go, Rust, Python, Solidity, Yul, TypeScript

---

*"Defense built by those who understand offense."*
