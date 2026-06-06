# =======================================================
# SISTEMA: FlowState AI - Inteligencia Conectada
# IMAGEN:  flowlexai-backend:latest
# AUTOR:   Gustavo Berton
# FECHA:   2026-05-12
# =======================================================

# ── Stage 1: Export dependencies ──────────────────────
FROM python:3.12-slim AS builder
WORKDIR /app

RUN pip install --no-cache-dir poetry==1.8.5
COPY pyproject.toml poetry.lock* ./
# Sincroniza lockfile con pyproject.toml y exporta sin hashes ni grupos dev
RUN poetry lock --no-update 2>/dev/null || true && \
    poetry export -f requirements.txt --output requirements.txt --without-hashes

# ── Stage 2: Runtime ──────────────────────────────────
FROM python:3.12-slim
WORKDIR /app

# libgomp1: requerido por faiss-cpu
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
EXPOSE 8000

# Cloud Run inyecta PORT; usamos 8000 por defecto
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
