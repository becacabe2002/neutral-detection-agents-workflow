FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY . .

# Install dependencies into a virtual environment
RUN uv sync

# Pre-download the embedding model to speed up container startup
RUN . .venv/bin/activate && python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"

# Ensure scripts are executable
RUN chmod +x scripts/import_mbfc_data.py

EXPOSE 8501

# The entrypoint script handles MBFC seeding and starting Streamlit
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
