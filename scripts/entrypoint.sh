#!/bin/bash
set -e

# Activate the virtual environment created by uv
if [ -f "/app/.venv/bin/activate" ]; then
    source /app/.venv/bin/activate
fi

# Ensure data directory exists
mkdir -p data

# Seed MBFC data if the SQLite database is missing
if [ ! -f "data/mbfc.sqlite" ]; then
    echo "MBFC database not found. Seeding from data/source_list.json..."
    if [ -f "data/source_list.json" ]; then
        python scripts/import_mbfc_data.py
    else
        echo "Warning: data/source_list.json not found. Skipping MBFC seeding."
    fi
else
    echo "MBFC database already exists."
fi

# Start the Streamlit application
echo "Starting Streamlit on port 8501..."
exec streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0
