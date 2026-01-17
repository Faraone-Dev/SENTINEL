# ═══════════════════════════════════════════════════════════════════════════════
#  SENTINEL SHIELD - Rust Decompiler Dockerfile
#  Multi-stage build for minimal image size
#  Author: SENTINEL Team
# ═══════════════════════════════════════════════════════════════════════════════

# Stage 1: Build
FROM rust:1.75-alpine AS builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache musl-dev pkgconfig openssl-dev

# Copy manifests
COPY Cargo.toml Cargo.lock ./

# Create dummy src to cache dependencies
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release
RUN rm -rf src

# Copy actual source
COPY src ./src

# Build release binary
RUN touch src/main.rs && cargo build --release

# Stage 2: Runtime
FROM alpine:3.19

RUN apk add --no-cache ca-certificates

COPY --from=builder /app/target/release/sentinel-decompile /usr/local/bin/

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:3000/health || exit 1

# Run in server mode
CMD ["sentinel-decompile", "--server", "--port", "3000"]

ENTRYPOINT ["sentinel-decompile"]
CMD ["--serve", "--port", "3000"]
