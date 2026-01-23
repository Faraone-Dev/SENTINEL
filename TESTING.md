# 🧪 SENTINEL - Test Suite Documentation

> **Comprehensive testing documentation for the SENTINEL security analysis platform**

---

## 📊 Test Summary

**Latest full run estimate:** **~89,959 total executions** (includes fuzz/property-based runs).

Use the sections below to run each suite locally. Some suites generate large fuzz sets and can take several minutes depending on your machine.

---

## 🔧 Prerequisites

### System Requirements

| Tool | Version | Installation |
|------|---------|--------------|
| Go | 1.22+ | `winget install -e --id GoLang.Go` |
| Python | 3.11+ | `winget install -e --id Python.Python.3.11` |
| Rust | stable | `winget install -e --id Rustlang.Rustup` |
| Foundry | 1.5.1+ | `curl -L https://foundry.paradigm.xyz \| bash` |
| MSYS2 | latest | `winget install -e --id MSYS2.MSYS2` |

### Python Dependencies

```bash
pip install pytest pytest-asyncio pytest-xprocess anyio
```

### Rust Toolchain (Windows)

```powershell
# Install MSYS2 GCC for Rust GNU toolchain
C:\msys64\usr\bin\bash.exe -lc "pacman -S --noconfirm mingw-w64-x86_64-gcc"

# Configure Rust to use GNU toolchain
rustup default stable-x86_64-pc-windows-gnu
```

### Foundry Setup

```bash
cd SENTINEL/contracts
forge install foundry-rs/forge-std --no-commit
```

---

## 🚀 Running Tests

### Go Tests (API Server)

```powershell
cd SENTINEL/api

# Run all tests
go test -v ./...

# Run with count (no cache)
go test -v -count=1 ./...

# Run specific test
go test -v -run TestScanner_RiskScoreCalculation ./cmd/server

# Run benchmarks
go test -bench=. ./...

# Run fuzz tests
go test -fuzz=FuzzRiskScore -fuzztime=30s ./cmd/server
```

**Expected Output:**
```
PASS
ok      sentinel/cmd/server     12.345s
--- PASS: TestScanner_RiskScoreCalculation (0.00s)
--- PASS: FuzzRiskScore (0.00s)
```

### Python Tests (Analyzer Engine)

```powershell
# From repo root - integration-style tests
$env:PYTHONPATH="$PWD/analyzer/src"
py -3.11 -m pytest tests/python -v

# Minimal output
$env:PYTHONPATH="$PWD/analyzer/src"
py -3.11 -m pytest tests/python -q --tb=no

# Run a specific test file
$env:PYTHONPATH="$PWD/analyzer/src"
py -3.11 -m pytest tests/python/test_core.py -v

# Run with coverage
$env:PYTHONPATH="$PWD/analyzer/src"
py -3.11 -m pytest tests/python --cov=analyzer --cov-report=html

# Local analyzer tests only
cd analyzer
py -3.11 -m pytest -q
```

### Rust Tests (EVM Decompiler)

```powershell
cd SENTINEL/decompiler

# Run all tests
cargo test

# Run with verbose output
cargo test -- --nocapture

# Run specific test
cargo test test_decompile_basic

# Run doc tests
cargo test --doc

# Run with release optimizations
cargo test --release
```

**Latest Output (2026-01-18):**
```
running 20031 tests
test result: ok. 20031 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
```

### Solidity Tests (Smart Contracts)

```powershell
cd SENTINEL/contracts

# Run all tests
forge test

# Run with verbosity
forge test -vvv

# Run with fuzz iterations
forge test --fuzz-runs 5000

# Run specific test file
forge test --match-path test/SentinelRegistry.t.sol

# Run specific test function
forge test --match-test testRegisterContract

# Run invariant tests
forge test --match-contract Invariant

# Gas report
forge test --gas-report
```

**Latest Output (2026-01-18):**
```
Ran 18 test suites in 78.84s (201.38s CPU time): 122 tests passed, 0 failed, 0 skipped (122 total tests)
Fuzz runs set to 30000 for fuzz tests.
```

---

## 📁 Test Structure

```
SENTINEL/
├── api/                          # Go API Server
│   └── cmd/server/
│       ├── main_test.go          # Unit tests
│       ├── benchmark_test.go     # Performance benchmarks
│       ├── integration_test.go   # Integration tests
│       └── fuzz_test.go          # Fuzz tests
│
├── analyzer/                     # Python Analyzer
│   └── tests/                     # Local unit tests
│
├── tests/python/                 # Python Analyzer
│   ├── test_core.py              # Core functionality
│   ├── test_pro_features.py      # Pro features
│   ├── test_integration.py       # Integration tests
│   └── test_analyzer.py          # Analyzer (requires src module)
│
├── decompiler/                   # Rust Decompiler
│   └── src/
│       ├── main.rs               # Unit tests (35)
│       └── server.rs             # Server tests
│
└── contracts/test/               # Solidity Smart Contracts
    ├── SentinelRegistry.t.sol           # Registry tests
    ├── SentinelRegistry.invariant.t.sol # Invariant tests
    ├── ApprovalRevoke.t.sol             # Approval tests
    └── ApprovalRevoke.fuzz.t.sol        # Fuzz tests
```

---

## ⚙️ Configuration Files

### foundry.toml (Solidity)

```toml
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
solc = "0.8.24"
optimizer = true
optimizer_runs = 200
fuzz = { runs = 5000, max_test_rejects = 100000 }
invariant = { runs = 1000, depth = 50 }

[profile.ci]
fuzz = { runs = 10000 }
```

### pytest.ini (Python)

```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
testpaths = tests/python
python_files = test_*.py
python_functions = test_*
```

---

## 🔍 Debugging Failed Tests

### Go

```powershell
# Run with race detector
go test -race -v ./...

# Run with CPU profile
go test -cpuprofile=cpu.prof -memprofile=mem.prof -v ./...
```

### Python

```powershell
# Show full traceback
python -m pytest tests/python -v --tb=long

# Stop on first failure
python -m pytest tests/python -x

# Debug with pdb
python -m pytest tests/python --pdb
```

### Rust

```powershell
# Show backtrace
$env:RUST_BACKTRACE=1; cargo test

# Run ignored tests
cargo test -- --ignored
```

### Solidity

```bash
# Maximum verbosity
forge test -vvvvv

# Show gas traces
forge test --gas-report -vvv

# Debug specific test
forge debug --debug test/SentinelRegistry.t.sol --sig "testRegisterContract()"
```

---

## 🏃 Quick Commands

| Action | Command |
|--------|---------|
| **All Go tests** | `cd api && go test -v ./...` |
| **All Python tests** | `cd SENTINEL && $env:PYTHONPATH="$PWD/analyzer/src"; py -3.11 -m pytest tests/python -q --tb=no` |
| **All Rust tests** | `cd decompiler && cargo test` |
| **All Solidity tests** | `cd contracts && forge test` |
| **Full test suite** | See [run-all-tests.ps1](#full-test-script) |

---

## 📝 Full Test Script

Create `run-all-tests.ps1`:

```powershell
#!/usr/bin/env pwsh
# SENTINEL - Complete Test Runner

$ErrorActionPreference = "Continue"
$root = $PSScriptRoot

Write-Host "`n========== SENTINEL TEST SUITE ==========" -ForegroundColor Cyan

# Go Tests
Write-Host "`n[1/4] Running Go Tests..." -ForegroundColor Yellow
Set-Location "$root/api"
$goResult = go test -v -count=1 ./... 2>&1
$goPassed = ($goResult | Select-String "--- PASS" | Measure-Object -Line).Lines
Write-Host "Go: $goPassed tests passed" -ForegroundColor Green

# Python Tests
Write-Host "`n[2/4] Running Python Tests..." -ForegroundColor Yellow
Set-Location $root
$env:PYTHONPATH = "$root/analyzer/src"
$pyResult = py -3.11 -m pytest tests/python -q --tb=no 2>&1
$pyLine = $pyResult | Select-String "passed"
Write-Host "Python: $pyLine" -ForegroundColor Green

# Rust Tests
Write-Host "`n[3/4] Running Rust Tests..." -ForegroundColor Yellow
Set-Location "$root/decompiler"
$rustResult = cargo test 2>&1
$rustLine = $rustResult | Select-String "test result"
Write-Host "Rust: $rustLine" -ForegroundColor Green

# Solidity Tests
Write-Host "`n[4/4] Running Solidity Tests..." -ForegroundColor Yellow
Set-Location "$root/contracts"
$solResult = forge test --fuzz-runs 1000 2>&1
$solLine = $solResult | Select-String "test suites"
Write-Host "Solidity: $solLine" -ForegroundColor Green

Write-Host "`n========== TEST COMPLETE ==========" -ForegroundColor Cyan
Set-Location $root
```

---

## 🐛 Known Issues

| Issue | Status | Workaround |
|-------|--------|------------|
| Pytest asyncio warning about `asyncio_default_fixture_loop_scope` | ℹ️ | Set it in pytest.ini or ignore the warning for now |
| Foundry not installed (`forge` not found) | ⚠️ | Install Foundry via `foundryup` and ensure it’s on PATH |
| Rust unsigned comparison warnings in omni tests | ℹ️ | Harmless warnings from generated tests |

---

## 📈 CI/CD Integration

### GitHub Actions Example

```yaml
name: SENTINEL Tests

on: [push, pull_request]

jobs:
  go-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
      - run: cd api && go test -v ./...

  python-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install pytest pytest-asyncio
      - run: python -m pytest tests/python -q

  rust-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions-rust-lang/setup-rust-toolchain@v1
      - run: cd decompiler && cargo test

  solidity-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: foundry-rs/foundry-toolchain@v1
      - run: cd contracts && forge test --fuzz-runs 5000
```

---

## 📞 Support

- **Issues**: Open a GitHub issue with test logs
- **Logs Location**: `SENTINEL/logs/`
- **Documentation**: See [README.md](README.md)

---

*Last updated: 2026-01-19*
