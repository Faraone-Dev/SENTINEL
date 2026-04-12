# ═══════════════════════════════════════════════════════════════════════════════
#  SENTINEL SHIELD - Go API Server Dockerfile
#  Multi-stage build for minimal image size
#  Author: Faraone-Dev
# ═══════════════════════════════════════════════════════════════════════════════

# Stage 1: Build
FROM golang:1.22-alpine AS builder

WORKDIR /app

# Install dependencies
RUN apk add --no-cache git ca-certificates tzdata

# Copy go mod files
COPY go.mod go.sum ./
RUN go mod download

# Copy source
COPY . .

# Build with optimizations
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags="-w -s -X main.Version=$(git describe --tags --always)" \
    -o /sentinel-api \
    ./cmd/server

# Stage 2: Runtime
FROM alpine:3.19

# Install CA certs and curl for healthcheck
RUN apk add --no-cache ca-certificates tzdata curl

# Create non-root user
RUN adduser -D -u 1000 sentinel

# Copy binary
COPY --from=builder /sentinel-api /sentinel-api

# Use non-root user
USER sentinel

# Expose port
EXPOSE 8080

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run
ENTRYPOINT ["/sentinel-api"]
