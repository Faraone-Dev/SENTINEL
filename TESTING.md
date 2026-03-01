# SENTINEL — Testing Guide

Complete test coverage across **6 components**, **5 languages**, **~90 000 test executions**.

## Overview

| Component | Language | Tests | Type | Command |
|-----------|----------|------:|------|---------|
| API | Go | 2 500+ | Unit · Integration · Fuzz · Benchmark | `go test ./...` |
| Frontend | TypeScript | 35 590 | Unit · Property-based · A11y | `npx vitest run` |
| Contracts | Solidity | 30 000+ | Unit · Fuzz (Foundry) | `forge test` |
| Analyzer | Python | 12 000+ | Unit · Property (Hypothesis) | `pytest` |
| Decompiler | Rust | 20 000+ | Unit · Integration | `cargo test` |
| E2E | Go + TS | 150+ | End-to-end | CI only |

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Go | ≥ 1.22 | API tests |
| Node.js | ≥ 18 | Frontend tests |
| Foundry | latest | Contract fuzz tests |
| Python | ≥ 3.11 | Analyzer tests |
| Rust | stable | Decompiler tests |
| Docker | ≥ 24 | Integration / E2E |

---

## Test Files

### Go API (`api/cmd/server/`)

| File | Scope |
|------|-------|
| `main_test.go` | Core endpoint unit tests |
| `comprehensive_test.go` | Full API surface coverage |
| `main_integration_test.go` | DB + Redis integration |
| `fuzz_test.go` | Input fuzzing (addresses, payloads) |
| `fuzz_comprehensive_test.go` | Extended fuzz campaigns |
| `mega_fuzz_test.go` | Long-running fuzz with corpus |
| `benchmark_test.go` | Latency and throughput benchmarks |

### Frontend (`frontend/src/__tests__/`)

| File | Tests | Scope |
|------|------:|-------|
| `ComponentUnits.test.tsx` | 54 | Isolated component rendering |
| `Components.test.tsx` | 10 000+ | Parameterized component variants |
| `PropertyBased.test.tsx` | 10 000+ | fast-check property invariants |
| `Integration.test.tsx` | 5 000+ | Multi-component flows |
| `Accessibility.test.tsx` | 5 000+ | WCAG / ARIA compliance |
| `AddressValidation.test.tsx` | 5 000+ | Address format edge cases |

### Solidity (`contracts/`)

Foundry fuzz tests with configurable runs (`foundry.toml → fuzz.runs`).

### Python Analyzer (`analyzer/`)

Hypothesis-based property tests + standard pytest unit tests.

### Rust Decompiler (`decompiler/`)

`cargo test` — unit + integration across all crates.

---

## Running Tests

```bash
# Go — all tests (unit + integration + fuzz)
cd api/cmd/server && go test -v -count=1 ./...

# Go — benchmarks only
go test -bench=. -benchmem ./...

# Go — fuzz (10 s per target)
go test -fuzz=FuzzAnalyzeWallet -fuzztime=10s

# Frontend
cd frontend && npx vitest run

# Contracts
cd contracts && forge test -vvv

# Analyzer
cd analyzer && pytest -v

# Decompiler
cd decompiler && cargo test
```

---

## Coverage

```bash
# Go
go test -coverprofile=cover.out ./... && go tool cover -html=cover.out

# Frontend
npx vitest run --coverage

# Contracts
forge coverage

# Python
pytest --cov=. --cov-report=html

# Rust
cargo tarpaulin --out Html
```

Current thresholds enforced in CI: **Go ≥ 80 %**, **Frontend ≥ 75 %**.

---

## CI/CD Integration

All tests run automatically on every push and PR via `.github/workflows/ci.yml`.

The pipeline spins up **PostgreSQL 15** and **Redis 7** as service containers for integration and E2E jobs. See [ci.yml](../.github/workflows/ci.yml) for full configuration.

**Jobs:** Lint → Test → Build → E2E → Security → Deploy

---

*Last updated: 2026-03-01*
