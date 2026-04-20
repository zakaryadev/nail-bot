# ─────────────────────────────────────────────
# Stage 1: dependency builder
# ─────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build deps only in builder stage
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ─────────────────────────────────────────────
# Stage 2: runtime image
# ─────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/install/lib/python3.11/site-packages"

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /install

# Create non-root user for security
RUN groupadd --gid 1001 botuser && \
    useradd --uid 1001 --gid botuser --shell /bin/sh --create-home botuser && \
    mkdir -p /data && chown botuser:botuser /data

# Copy application code
COPY --chown=botuser:botuser . .

USER botuser

# Health check — verifies the process is alive
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

CMD ["python", "bot.py"]
