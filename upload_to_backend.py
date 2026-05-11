"""Upload PowerMocker-generated CSV data to the Energy Community FastAPI backend.

Reads `haz_adatok/osszes_haz_adat.csv` (produced by generator.py) and POSTs it
to the `/webhook/powermocker` endpoint in daily batches.

Usage:
    python upload_to_backend.py                 # uploads all data
    python upload_to_backend.py --days 7        # uploads only first 7 days
    POWERMOCKER_WEBHOOK_URL=... python upload_to_backend.py
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
MASTER_CSV = ROOT / "haz_adatok" / "osszes_haz_adat.csv"
DEFAULT_URL = os.environ.get(
    "POWERMOCKER_WEBHOOK_URL", "http://127.0.0.1:8000/webhook/powermocker"
)
CHUNK_SIZE = 576  # 6 houses x 96 quarter-hours = 1 day


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="FastAPI webhook URL")
    parser.add_argument("--csv", default=str(MASTER_CSV), help="Master CSV path")
    parser.add_argument("--days", type=int, default=0, help="Only upload first N days (0 = all)")
    parser.add_argument("--drop-first", action="store_true", help="Call /api/data-drop before uploading")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}. Run generator.py first.", file=sys.stderr)
        return 1

    print(f"Reading {csv_path}...")
    df = pd.read_csv(csv_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"]).apply(lambda x: x.isoformat())
    records = df.to_dict("records")
    if args.days and args.days > 0:
        records = records[: CHUNK_SIZE * args.days]
    total = len(records)
    print(f"Uploading {total} rows to {args.url}")

    if args.drop_first:
        base = args.url.replace("/webhook/powermocker", "")
        drop_url = base + "/api/data-drop"
        r = requests.post(drop_url, timeout=30)
        print(f"Data drop: {r.status_code}")

    uploaded = 0
    inserted = 0
    t0 = time.time()
    for i in range(0, total, CHUNK_SIZE):
        chunk = records[i : i + CHUNK_SIZE]
        payload = {"type": "batch_update", "data": chunk}
        r = requests.post(args.url, json=payload, timeout=120)
        r.raise_for_status()
        body = r.json()
        uploaded += body.get("received", len(chunk))
        inserted += body.get("inserted", 0)
        if (i // CHUNK_SIZE) % 10 == 0:
            print(f"  {uploaded}/{total} rows (inserted={inserted}, {r.status_code})")
    print(f"Done. Uploaded={uploaded}, inserted={inserted}, in {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
