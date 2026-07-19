FROM python:3.13-slim AS base

# System deps for PyMuPDF and general build tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Python dependencies (cached layer)
COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

# Copy application code and data
COPY langgraph.json ./
COPY app/ ./app/
COPY data/ ./data/
COPY main.py ./

# The .env is injected at runtime (docker run --env-file .env)
# Do NOT bake secrets into the image.

EXPOSE 2024

CMD ["uv", "run", "langgraph", "up", "--host", "0.0.0.0", "--port", "2024"]
