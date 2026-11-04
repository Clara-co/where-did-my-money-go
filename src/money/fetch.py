"""Download the raw data from the two official APIs and cache it as JSON.

BLS Public Data API v2 (CPI-U, U.S. city average, not seasonally adjusted)
    https://www.bls.gov/developers/
    Works without a key: up to 10 years per request, so 2015 to 2025 is split
    into two requests. Set BLS_API_KEY to raise the daily limit.

BEA Regional API (Regional Price Parities by state, table SARPP)
    https://apps.bea.gov/api/signup/
    Needs a free key in BEA_API_KEY.

Raw responses are saved to data/raw/ so later runs work offline and the exact
inputs behind every number are kept with the repo.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

BLS_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BEA_URL = "https://apps.bea.gov/api/data"

# CPI-U, U.S. city average, not seasonally adjusted. The category names match
# the five categories in the original report, plus All items as the benchmark.
CPI_SERIES = {
    "CUUR0000SA0": "All items",
    "CUUR0000SAH1": "Shelter",
    "CUUR0000SAT": "Transportation",
    "CUUR0000SETB": "Motor fuel",
    "CUUR0000SAF1": "Food",
    "CUUR0000SAM": "Medical care",
    "CUUR0000SAR": "Recreation",
}

CPI_START, CPI_END = 2015, 2025
RPP_START, RPP_END = 2014, 2024
RPP_LINE_ALL_ITEMS = 1  # SARPP line 1 = RPPs: All items


def _year_windows(start: int, end: int, size: int = 10) -> list[tuple[int, int]]:
    """Split [start, end] into windows the BLS API will accept (<= size years)."""
    windows, y = [], start
    while y <= end:
        windows.append((y, min(y + size - 1, end)))
        y += size
    return windows


def _post_json(url: str, payload: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "where-did-my-money-go/1.0"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def _get_json(url: str, params: dict) -> dict:
    full = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(full, headers={"User-Agent": "where-did-my-money-go/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def _scrub(obj, secret: str | None):
    """Remove an API key from a response before it is saved.

    BEA echoes the request, including UserID, back in its response. The raw
    files are meant to be committed, so any value equal to the key becomes
    "REDACTED", and BEA's echoed Request block is dropped.
    """
    if isinstance(obj, dict):
        return {k: _scrub(v, secret) for k, v in obj.items() if k != "Request"}
    if isinstance(obj, list):
        return [_scrub(v, secret) for v in obj]
    if secret and isinstance(obj, str) and secret in obj:
        return obj.replace(secret, "REDACTED")
    return obj


def fetch_cpi(out_dir: Path = RAW_DIR) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    key = os.environ.get("BLS_API_KEY")
    paths = []
    for start, end in _year_windows(CPI_START, CPI_END):
        payload = {"seriesid": list(CPI_SERIES), "startyear": str(start), "endyear": str(end)}
        if key:
            payload["registrationkey"] = key
        data = _post_json(BLS_URL, payload)
        if data.get("status") != "REQUEST_SUCCEEDED":
            raise RuntimeError(f"BLS request {start}-{end} failed: {data.get('message')}")
        path = out_dir / f"bls_cpi_{start}_{end}.json"
        path.write_text(json.dumps(_scrub(data, key), indent=1))
        paths.append(path)
    return paths


def fetch_rpp(out_dir: Path = RAW_DIR) -> Path:
    key = os.environ.get("BEA_API_KEY")
    if not key:
        raise SystemExit("Set BEA_API_KEY first (free signup: https://apps.bea.gov/api/signup/)")
    out_dir.mkdir(parents=True, exist_ok=True)
    params = {
        "UserID": key,
        "method": "GetData",
        "datasetname": "Regional",
        "TableName": "SARPP",
        "LineCode": RPP_LINE_ALL_ITEMS,
        "GeoFips": "STATE",
        "Year": ",".join(str(y) for y in range(RPP_START, RPP_END + 1)),
        "ResultFormat": "json",
    }
    data = _get_json(BEA_URL, params)
    if "Error" in data.get("BEAAPI", {}).get("Results", {}):
        raise RuntimeError(f"BEA request failed: {data['BEAAPI']['Results']['Error']}")
    path = out_dir / "bea_sarpp_states.json"
    path.write_text(json.dumps(_scrub(data, key), indent=1))
    return path


if __name__ == "__main__":
    for p in fetch_cpi():
        print("saved", p)
    print("saved", fetch_rpp())
