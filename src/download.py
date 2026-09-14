"""Download the Government Procurement via GeBIZ dataset from data.gov.sg.

Uses the data.gov.sg Open API (v1) poll-download flow:
1. GET /v1/public/api/datasets/{dataset_id}/poll-download
   -> returns a short-lived, pre-signed S3 URL for the CSV export
2. Download that URL directly

Dataset page: https://data.gov.sg/datasets/d_acde1106003906a75c3fa052592f2fcb/view
"""

from __future__ import annotations

import sys
from pathlib import Path

import requests

DATASET_ID = "d_acde1106003906a75c3fa052592f2fcb"
POLL_URL = f"https://api-open.data.gov.sg/v1/public/api/datasets/{DATASET_ID}/poll-download"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "gebiz_procurement.csv"


def get_download_url() -> str:
    resp = requests.get(POLL_URL, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("code") != 0:
        raise RuntimeError(f"poll-download failed: {payload}")
    return payload["data"]["url"]


def download(output_path: Path = OUTPUT_PATH) -> Path:
    url = get_download_url()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    return output_path


if __name__ == "__main__":
    path = download()
    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"Downloaded to {path} ({size_mb:.2f} MB)", file=sys.stderr)
