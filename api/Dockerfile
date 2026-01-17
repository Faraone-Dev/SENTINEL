# ═══════════════════════════════════════════════════════════════════════════════
#  SENTINEL SHIELD - Go API Server Dockerfile
#  Multi-stage build for minimal image size
#  Author: SENTINEL Team
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
FROM scratch

# Copy CA certificates for HTTPS
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo

# Copy binary
COPY --from=builder /sentinel-api /sentinel-api

# Expose port
EXPOSE 8080

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["/sentinel-api", "health"]

# Run
ENTRYPOINT ["/sentinel-api"]
