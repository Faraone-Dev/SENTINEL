# 🧪 SENTINEL SHIELD - Testing Guide

## Test Suite Overview

SENTINEL has **60,000+** automated tests across 4 languages.

| Language | Test Count | Location           |
| -------- | ---------- | ------------------ |
| Python   | ~29,000    | `tests/python/`    |
| Go       | ~10,000    | `tests/go/`        |
| Solidity | ~21,000    | `tests/solidity/`  |
| Rust     | ~70        | `tests/rust/`      |

---

## Running Tests

### All Tests

```bash
make test
```

### Python Tests

```bash
cd analyzer
pytest ../tests/python/ -v
# Or with coverage
pytest ../tests/python/ --cov=src --cov-report=html
```

### Go Tests

```bash
cd api
go test ./... -v
# With race detection
go test ./... -race
# With coverage
go test ./... -coverprofile=coverage.out
```

### Rust Tests

```bash
cd decompiler
cargo test
# With output
cargo test -- --nocapture
```

### Solidity Tests

```bash
cd contracts
forge test
# With verbosity
forge test -vvv
# With gas report
forge test --gas-report
# Fuzz tests (more runs)
forge test --fuzz-runs 10000
```

---

## Test Categories

### Python Test Files

| File                   | Tests  | Description                          |
| ---------------------- | ------ | ------------------------------------ |
| `test_mega_fuzzing.py` | 5,000+ | Address/tx validation, gas estimation |
| `test_edge_cases.py`   | 5,000+ | Boundary conditions                  |
| `test_pro_features.py` | 5,000+ | Advanced features                    |
| `test_fuzzing.py`      | 3,000+ | Random input testing                 |
| `test_analyzer.py`     | 500+   | Core analyzer tests                  |

### Go Test Files

| File                       | Tests  | Description          |
| -------------------------- | ------ | -------------------- |
| `mega_fuzz_test.go`        | 5,000+ | Transaction validation |
| `fuzz_comprehensive_test.go` | 3,000+ | RPC responses         |
| `comprehensive_test.go`    | 1,000+ | Integration tests    |
| `main_test.go`             | 500+   | Unit tests           |

### Solidity Test Files

| File                            | Tests        | Description       |
| ------------------------------- | ------------ | ----------------- |
| `SentinelRegistry.fuzz.t.sol`   | 11 × 1000 runs | Fuzz testing      |
| `SentinelRegistry.invariant.t.sol` | 7 × 256 runs  | Invariant testing |
| `SentinelRegistry.t.sol`        | 50+          | Unit tests        |
| `SentinelRegistry.gas.t.sol`    | 20+          | Gas benchmarks    |
| `SentinelRegistry.security.t.sol` | 30+          | Security tests    |

### Rust Test Files

| File                 | Tests | Description                 |
| -------------------- | ----- | --------------------------- |
| `tests.rs`           | 34    | Opcode, disassembler, CFG   |
| `extended_tests.rs`  | 32    | Security analysis           |

---

## CI/CD

Tests run automatically on:
- Push to `main`
- Pull requests
- Scheduled nightly

See `.github/workflows/ci.yml` for configuration.
