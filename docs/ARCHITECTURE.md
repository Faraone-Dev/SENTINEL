# 🏗️ SENTINEL SHIELD - Architecture

## Overview

SENTINEL is a multi-chain wallet security scanner built with a microservices architecture.

```text
┌─────────────────────────────────────────────────────────────────┐
│                      SENTINEL SHIELD                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              FRONTEND (React + TypeScript)               │    │
│  │                    Port: 3000                            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            │                                     │
│                            ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    API SERVER (Go)                       │    │
│  │                    Port: 8080                            │    │
│  │        Fast, concurrent, multi-chain RPC handling        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            │                                     │
│         ┌──────────────────┼──────────────────┐                 │
│         ▼                  ▼                  ▼                 │
│  ┌────────────┐    ┌────────────────┐   ┌──────────────┐       │
│  │ DECOMPILER │    │ RISK ANALYZER  │   │   DATABASE   │       │
│  │   (Rust)   │    │   (Python)     │   │  (Postgres)  │       │
│  │ Port: 3001 │    │   Port: 5000   │   │  Port: 5432  │       │
│  └────────────┘    └────────────────┘   └──────────────┘       │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │            ON-CHAIN CONTRACTS (Solidity + Yul)           │    │
│  │         Gas-optimized registry and revoke helpers        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Go API Server (`api/`)

- **Purpose**: Main entry point, multi-chain RPC orchestration
- **Port**: 8080
- **Features**:
  - Concurrent scanning across 16 EVM chains
  - Alchemy + Etherscan API integration
  - Rate limiting and caching
  - Known spender/token databases

### 2. Rust Decompiler (`decompiler/`)

- **Purpose**: EVM bytecode analysis
- **Port**: 3001
- **Features**:
  - Opcode parsing
  - Control Flow Graph generation
  - Function selector extraction
  - Dangerous opcode detection

### 3. Python Analyzer (`analyzer/`)

- **Purpose**: Heuristic vulnerability detection
- **Port**: 5000
- **Features**:
  - Honeypot detection
  - Rug pull pattern matching
  - Reentrancy analysis
  - Risk scoring

### 4. React Frontend (`frontend/`)

- **Purpose**: User interface
- **Port**: 3000
- **Features**:
  - Wallet connection (RainbowKit)
  - Multi-chain scanning
  - Approval management
  - One-click revoke

### 5. Solidity Contracts (`contracts/`)

- **Purpose**: On-chain batch revocation
- **Features**:
  - ERC20/ERC721/ERC1155 support
  - Gas-optimized with Yul
  - Permissionless design

## Supported Chains (16)

| Ethereum L2s   | Alt L1s     |
| -------------- | ----------- |
| Ethereum       | BNB Chain   |
| Arbitrum       | Polygon PoS |
| Optimism       | Avalanche   |
| Base           | Fantom      |
| zkSync Era     | Cronos      |
| Linea          | Gnosis      |
| Scroll         | Celo        |
| Polygon zkEVM  | Moonbeam    |

## Data Flow

1. User enters wallet address in frontend
2. Frontend calls Go API `/api/v1/scan`
3. Go API queries 16 chains in parallel via Alchemy/Etherscan
4. For each contract found, Go API optionally calls:
   - Rust Decompiler for bytecode analysis
   - Python Analyzer for vulnerability detection
5. Results aggregated and returned to frontend
6. User can revoke approvals via SentinelRegistry contract
