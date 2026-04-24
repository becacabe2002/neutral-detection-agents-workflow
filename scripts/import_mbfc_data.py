import json
import sqlite3
import sys
import os
from pathlib import Path

# since we are under /scripts/import_mbfc_data.py
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.utils.domain_parser import canonicalize_domain

DB_PATH = project_root / "data" / "mbfc.sqlite"
JSON_PATH = project_root / "data" / "source_list.json"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT UNIQUE NOT NULL,
    name TEXT,
    bias TEXT,
    factual_reporting TEXT,
    credibility TEXT,
    country TEXT,
    media_type TEXT,
    mbfc_url TEXT,
    mbfc_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_sources_domain ON sources(domain);
"""

def run_import():
    os.makedirs(DB_PATH.parent, exist_ok=True)

    if not os.path.exists(JSON_PATH):
        print(f"Error: JSON file not found at {JSON_PATH}")
        return

    print(f"Loading data from {JSON_PATH} ...")
    with open(JSON_PATH, "r") as f:
        data = json.load(f)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Initialize db schema ...")
    cursor.executescript(SCHEMA)

    print("Importing sources from json ...")
    count = 0
    skipped = 0

    for item in data:
        raw_url = item.get("Source URL", "")

        if not raw_url or raw_url.strip().upper() == "DEAD":
            skipped += 1
            continue
        
        domain = canonicalize_domain(raw_url)
        if not domain:
            skipped += 1
            continue

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO sources (domain, name, bias, factual_reporting, credibility, country, media_type, mbfc_url, mbfc_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (domain, 
                 item.get("Source"),
                 item.get("Bias"),
                 item.get("Factual Reporting"),
                 item.get("Credibility"),
                 item.get("Country"),
                 item.get("Media Type"),
                 item.get("MBFC URL"),
                 str(item.get("Source ID#"))
                 ))
            count += 1
        except Exception as e:
            print(f"\nError importing {domain}: {e}.")

    conn.commit()
    conn.close()
    print("--- Import Completed ---")
    print(f"Imported: {count} instances; Skipped: {skipped}")
    print(f"DB saved to: {DB_PATH}")

if __name__ == "__main__":
    run_import()