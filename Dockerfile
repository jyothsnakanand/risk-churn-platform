FROM python:3.11-slim

WORKDIR /app

# Install system dependencies with retry for transient package issues
RUN apt-get update && apt-get install -y --fix-missing \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./

# Install uv for faster dependency installation
RUN pip install uv

# Install dependencies
RUN uv pip install --system -e .

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create models directory
RUN mkdir -p models/v1 models/v2

# Expose ports
EXPOSE 8080 9000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Run application
CMD ["uvicorn", "src.risk_churn_platform.api.rest_api:app", "--host", "0.0.0.0", "--port", "8080"]
