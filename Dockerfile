# Multi-stage Dockerfile for Forex ML Pipeline

# Base stage with common dependencies
FROM python:3.9-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Development stage
FROM base as development

COPY . .
RUN pip install --no-cache-dir \
    ray[tune] \
    mlflow \
    optuna \
    pytest \
    black \
    flake8

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Training stage
FROM base as training

COPY . .
RUN pip install --no-cache-dir \
    ray[tune] \
    mlflow \
    optuna \
    xgboost \
    scikit-learn

# Set MLflow tracking URI
ENV MLFLOW_TRACKING_URI=file:./mlruns

CMD ["python", "scripts/train_models.py"]

# Production API stage
FROM base as production

COPY api/ .
COPY exported_models/ ./exported_models/

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]