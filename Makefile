# ═══════════════════════════════════════════════════════════════════════════════
#  ██████╗ ███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗
# ██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║
# ███████╗ █████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║
# ╚════██║ ██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║
# ███████║ ███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗
# ╚══════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝
#
#  SENTINEL SHIELD - Build & Development Makefile
#  Author: SENTINEL Team
# ═══════════════════════════════════════════════════════════════════════════════

.PHONY: all build run test clean docker-build docker-up docker-down help

# Colors for terminal output
GREEN  := \033[0;32m
YELLOW := \033[0;33m
CYAN   := \033[0;36m
RESET  := \033[0m

# Project directories
API_DIR      := api
DECOMPILER_DIR := decompiler
ANALYZER_DIR := analyzer
FRONTEND_DIR := frontend
CONTRACTS_DIR := contracts

# ═══════════════════════════════════════════════════════════════════════════════
#                              DEFAULT TARGET
# ═══════════════════════════════════════════════════════════════════════════════

all: help

# ═══════════════════════════════════════════════════════════════════════════════
#                              BUILD TARGETS
# ═══════════════════════════════════════════════════════════════════════════════

## Build all components
build: build-api build-decompiler build-frontend build-contracts
	@echo "$(GREEN)✓ All components built successfully$(RESET)"

## Build Go API server
build-api:
	@echo "$(CYAN)Building Go API server...$(RESET)"
	cd $(API_DIR) && go build -o ../bin/sentinel-api ./cmd/server

## Build Rust decompiler
build-decompiler:
	@echo "$(CYAN)Building Rust decompiler...$(RESET)"
	cd $(DECOMPILER_DIR) && cargo build --release
	cp $(DECOMPILER_DIR)/target/release/sentinel-decompile bin/

## Build React frontend
build-frontend:
	@echo "$(CYAN)Building React frontend...$(RESET)"
	cd $(FRONTEND_DIR) && npm install && npm run build

## Build Solidity contracts
build-contracts:
	@echo "$(CYAN)Compiling Solidity contracts...$(RESET)"
	cd $(CONTRACTS_DIR) && forge build

# ═══════════════════════════════════════════════════════════════════════════════
#                              RUN TARGETS
# ═══════════════════════════════════════════════════════════════════════════════

## Run the API server locally
run-api:
	@echo "$(CYAN)Starting API server on :8080...$(RESET)"
	cd $(API_DIR) && go run ./cmd/server

## Run the Rust decompiler CLI
run-decompiler:
	@echo "$(CYAN)Running decompiler...$(RESET)"
	cd $(DECOMPILER_DIR) && cargo run -- --help

## Run Python analyzer
run-analyzer:
	@echo "$(CYAN)Starting Python analyzer...$(RESET)"
	cd $(ANALYZER_DIR) && python -m src.analyzer

## Run frontend dev server
run-frontend:
	@echo "$(CYAN)Starting frontend dev server...$(RESET)"
	cd $(FRONTEND_DIR) && npm run dev

## Run all services (requires Docker)
run: docker-up
	@echo "$(GREEN)All services running!$(RESET)"
	@echo "$(CYAN)Frontend: http://localhost$(RESET)"
	@echo "$(CYAN)API: http://localhost:8080$(RESET)"

# ═══════════════════════════════════════════════════════════════════════════════
#                              TEST TARGETS
# ═══════════════════════════════════════════════════════════════════════════════

## Run all tests
test: test-api test-decompiler test-analyzer test-contracts
	@echo "$(GREEN)✓ All tests passed$(RESET)"

## Test Go API (tests in tests/go/)
test-api:
	@echo "$(CYAN)Testing Go API...$(RESET)"
	cd $(API_DIR) && go test -v ./...
	@echo "$(CYAN)Running additional Go tests from tests/go/...$(RESET)"
	go test -v ./tests/go/...

## Test Rust decompiler
test-decompiler:
	@echo "$(CYAN)Testing Rust decompiler...$(RESET)"
	cd $(DECOMPILER_DIR) && cargo test

## Test Python analyzer (tests in tests/python/)
test-analyzer:
	@echo "$(CYAN)Testing Python analyzer...$(RESET)"
	cd $(ANALYZER_DIR) && pytest -v ../tests/python/

## Test Solidity contracts (tests in tests/solidity/)
test-contracts:
	@echo "$(CYAN)Testing Solidity contracts...$(RESET)"
	cd $(CONTRACTS_DIR) && forge test -v
	@echo "$(CYAN)Running additional Solidity tests from tests/solidity/...$(RESET)"
	cd $(CONTRACTS_DIR) && forge test -v --match-path ../tests/solidity/*.sol

# ═══════════════════════════════════════════════════════════════════════════════
#                              DOCKER TARGETS
# ═══════════════════════════════════════════════════════════════════════════════

## Build all Docker images
docker-build:
	@echo "$(CYAN)Building Docker images...$(RESET)"
	docker-compose build

## Start all containers
docker-up:
	@echo "$(CYAN)Starting all containers...$(RESET)"
	docker-compose up -d
	@echo "$(GREEN)✓ All containers started$(RESET)"

## Stop all containers
docker-down:
	@echo "$(CYAN)Stopping all containers...$(RESET)"
	docker-compose down

## View container logs
docker-logs:
	docker-compose logs -f

## Rebuild and restart
docker-restart: docker-down docker-build docker-up

# ═══════════════════════════════════════════════════════════════════════════════
#                              UTILITY TARGETS
# ═══════════════════════════════════════════════════════════════════════════════

## Install all dependencies
install:
	@echo "$(CYAN)Installing dependencies...$(RESET)"
	cd $(API_DIR) && go mod download
	cd $(DECOMPILER_DIR) && cargo fetch
	cd $(ANALYZER_DIR) && pip install -r requirements.txt
	cd $(FRONTEND_DIR) && npm install
	@echo "$(GREEN)✓ All dependencies installed$(RESET)"

## Clean build artifacts
clean:
	@echo "$(CYAN)Cleaning build artifacts...$(RESET)"
	rm -rf bin/
	rm -rf $(DECOMPILER_DIR)/target
	rm -rf $(FRONTEND_DIR)/dist
	rm -rf $(FRONTEND_DIR)/node_modules
	rm -rf $(CONTRACTS_DIR)/out
	rm -rf $(CONTRACTS_DIR)/cache
	rm -rf $(ANALYZER_DIR)/__pycache__
	rm -rf $(ANALYZER_DIR)/.pytest_cache
	@echo "$(GREEN)✓ Cleaned$(RESET)"

## Format all code
fmt:
	@echo "$(CYAN)Formatting code...$(RESET)"
	cd $(API_DIR) && go fmt ./...
	cd $(DECOMPILER_DIR) && cargo fmt
	cd $(FRONTEND_DIR) && npm run lint -- --fix
	cd $(CONTRACTS_DIR) && forge fmt
	@echo "$(GREEN)✓ Formatted$(RESET)"

## Lint all code
lint:
	@echo "$(CYAN)Linting code...$(RESET)"
	cd $(API_DIR) && golangci-lint run
	cd $(DECOMPILER_DIR) && cargo clippy
	cd $(FRONTEND_DIR) && npm run lint
	cd $(CONTRACTS_DIR) && forge fmt --check

## Generate API documentation
docs:
	@echo "$(CYAN)Generating documentation...$(RESET)"
	cd $(API_DIR) && swag init -g cmd/server/main.go
	cd $(DECOMPILER_DIR) && cargo doc --no-deps
	@echo "$(GREEN)✓ Documentation generated$(RESET)"

# ═══════════════════════════════════════════════════════════════════════════════
#                              DEPLOYMENT
# ═══════════════════════════════════════════════════════════════════════════════

## Deploy contracts to testnet
deploy-testnet:
	@echo "$(CYAN)Deploying contracts to Sepolia...$(RESET)"
	cd $(CONTRACTS_DIR) && forge script script/Deploy.s.sol --rpc-url sepolia --broadcast

## Deploy contracts to mainnet (BE CAREFUL!)
deploy-mainnet:
	@echo "$(YELLOW)⚠ DEPLOYING TO MAINNET$(RESET)"
	@read -p "Are you sure? [y/N] " confirm; \
	if [ "$$confirm" = "y" ]; then \
		cd $(CONTRACTS_DIR) && forge script script/Deploy.s.sol --rpc-url mainnet --broadcast; \
	fi

# ═══════════════════════════════════════════════════════════════════════════════
#                              HELP
# ═══════════════════════════════════════════════════════════════════════════════

## Show this help message
help:
	@echo ""
	@echo "$(CYAN)╔═══════════════════════════════════════════════════════════════════════════╗$(RESET)"
	@echo "$(CYAN)║$(RESET)  $(GREEN)SENTINEL SHIELD$(RESET) - Multi-chain Wallet Security Scanner                   $(CYAN)║$(RESET)"
	@echo "$(CYAN)╚═══════════════════════════════════════════════════════════════════════════╝$(RESET)"
	@echo ""
	@echo "$(YELLOW)Usage:$(RESET)"
	@echo "  make <target>"
	@echo ""
	@echo "$(YELLOW)Build Targets:$(RESET)"
	@echo "  $(GREEN)build$(RESET)            Build all components"
	@echo "  $(GREEN)build-api$(RESET)        Build Go API server"
	@echo "  $(GREEN)build-decompiler$(RESET) Build Rust decompiler"
	@echo "  $(GREEN)build-frontend$(RESET)   Build React frontend"
	@echo "  $(GREEN)build-contracts$(RESET)  Compile Solidity contracts"
	@echo ""
	@echo "$(YELLOW)Run Targets:$(RESET)"
	@echo "  $(GREEN)run$(RESET)              Start all services with Docker"
	@echo "  $(GREEN)run-api$(RESET)          Run API server locally"
	@echo "  $(GREEN)run-frontend$(RESET)     Run frontend dev server"
	@echo ""
	@echo "$(YELLOW)Test Targets:$(RESET)"
	@echo "  $(GREEN)test$(RESET)             Run all tests"
	@echo "  $(GREEN)test-api$(RESET)         Test Go API"
	@echo "  $(GREEN)test-decompiler$(RESET)  Test Rust decompiler"
	@echo "  $(GREEN)test-contracts$(RESET)   Test Solidity contracts"
	@echo ""
	@echo "$(YELLOW)Docker Targets:$(RESET)"
	@echo "  $(GREEN)docker-build$(RESET)     Build all Docker images"
	@echo "  $(GREEN)docker-up$(RESET)        Start all containers"
	@echo "  $(GREEN)docker-down$(RESET)      Stop all containers"
	@echo ""
	@echo "$(YELLOW)Utility Targets:$(RESET)"
	@echo "  $(GREEN)install$(RESET)          Install all dependencies"
	@echo "  $(GREEN)clean$(RESET)            Clean build artifacts"
	@echo "  $(GREEN)fmt$(RESET)              Format all code"
	@echo "  $(GREEN)lint$(RESET)             Lint all code"
	@echo ""
