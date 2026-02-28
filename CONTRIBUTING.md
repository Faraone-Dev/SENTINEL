# Contributing to SENTINEL SHIELD

Thank you for your interest in contributing to SENTINEL SHIELD! 🛡️

## Getting Started

### Prerequisites

- Go 1.22+
- Rust 1.75+
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- Foundry (for smart contracts)

### Setup

```bash
# Clone the repository
git clone https://github.com/sentinel-team/sentinel.git
cd sentinel

# Install all dependencies
make install

# Copy environment file
cp config/.env.example config/.env

# Start development environment
make docker-up
```

## Development Workflow

### Branch Naming

- `feature/` - New features
- `fix/` - Bug fixes
- `refactor/` - Code refactoring
- `docs/` - Documentation updates
- `test/` - Test additions/updates

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(api): add batch revoke endpoint
fix(decompiler): handle truncated bytecode
docs(readme): update installation instructions
test(contracts): add fuzz tests for registry
```

### Code Style

- **Go**: `gofmt` + `golangci-lint`
- **Rust**: `rustfmt` + `clippy`
- **Python**: `ruff` + `mypy`
- **TypeScript**: ESLint + Prettier
- **Solidity**: `forge fmt`

Run all formatters:
```bash
make fmt
```

Run all linters:
```bash
make lint
```

### Testing

```bash
# Run all tests
make test

# Run specific tests
make test-api
make test-decompiler
make test-analyzer
make test-contracts
```

**Latest full run estimate:** **~89,959 total executions** (includes fuzz/property-based runs).

## Pull Request Process

1. Fork the repository
2. Create your feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Update documentation if needed
6. Submit PR with clear description

### PR Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Linting passes
- [ ] Changelog updated (if applicable)
- [ ] Security implications considered

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend   │────▶│   Go API    │────▶│  PostgreSQL │
│  (React)    │     │   Server    │     │  (Cache)    │
└─────────────┘     └─────┬───────┘     └─────────────┘
                          │
                    ┌─────┴─────┐
                    ▼           ▼
            ┌───────────┐ ┌───────────┐
            │   Rust    │ │  Python   │
            │Decompiler │ │ Analyzer  │
            └───────────┘ └───────────┘
```

## Code of Conduct

Be respectful, inclusive, and constructive. We're all here to build something great together.

## Questions?

Open a discussion on GitHub or reach out to the maintainers.

---

*Happy coding!* 🚀
