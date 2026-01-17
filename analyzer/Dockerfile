# ═══════════════════════════════════════════════════════════════════════════════
#  SENTINEL SHIELD - Python Analyzer Dockerfile
#  Author: SENTINEL Team
# ═══════════════════════════════════════════════════════════════════════════════

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src ./src

# Create non-root user
RUN useradd -m -u 1000 sentinel
USER sentinel

EXPOSE 5000

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

CMD ["python", "-m", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "5000"]
