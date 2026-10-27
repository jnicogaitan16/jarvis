FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# Source
COPY src/ src/
COPY config/ config/
COPY data/ data/

# Default: web dashboard
EXPOSE 8000
CMD ["python", "-m", "jarvis", "serve", "--host", "0.0.0.0"]
