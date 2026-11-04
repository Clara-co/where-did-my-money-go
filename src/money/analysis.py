"""Turn the cached API responses into tidy tables and the headline numbers."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .fetch import CPI_SERIES, RAW_DIR

FED_TARGET_PCT = 2.0


# --------------------------------------------------------------------------- CPI
def parse_bls(paths: list[Path]) -> pd.DataFrame:
    """Monthly CPI observations as one row per (series, year, month)."""
    rows = []
    for path in paths:
        data = json.loads(Path(path).read_text())
        for series in data["Results"]["series"]:
            sid = series["seriesID"]
            for obs in series["data"]:
                period = obs["period"]
                if not period.startswith("M") or period == "M13":
                    continue  # skip annual-average rows; we compute our own
                value = obs["value"]
                if value in ("-", ""):
                    continue  # BLS uses "-" for months with no data
                rows.append(
                    {
                        "series_id": sid,
                        "category": CPI_SERIES.get(sid, sid),
                        "year": int(obs["year"]),
                        "month": int(period[1:]),
                        "index": float(value),
                    }
                )
    df = pd.DataFrame(rows).drop_duplicates(["series_id", "year", "month"])
    return df.sort_values(["category", "year", "month"]).reset_index(drop=True)


def annual_average(monthly: pd.DataFrame) -> pd.DataFrame:
    """Mean of the available months for each category and year.

    `months` records how many months went into each average, so a year with
    missing months (for example, October 2025, when BLS did not collect CPI data
    during the federal shutdown) is visible instead of silently averaged.
    """
    g = monthly.groupby(["category", "year"])["index"]
    return g.agg(index="mean", months="size").reset_index()


def purchasing_power(annual: pd.DataFrame, base_year: int, end_year: int) -> pd.DataFrame:
    """What $1 spent in `base_year` buys in `end_year`, by category.

    A dollar's purchasing power falls in proportion to the price index:
    value = CPI(base) / CPI(end).
    """
    wide = annual.pivot(index="category", columns="year", values="index")
    out = pd.DataFrame(
        {
            f"cpi_{base_year}": wide[base_year],
            f"cpi_{end_year}": wide[end_year],
        }
    )
    out["price_change_pct"] = 100 * (out[f"cpi_{end_year}"] / out[f"cpi_{base_year}"] - 1)
    out["cents_per_base_dollar"] = 100 * out[f"cpi_{base_year}"] / out[f"cpi_{end_year}"]
    out["cost_of_base_100"] = 100 * out[f"cpi_{end_year}"] / out[f"cpi_{base_year}"]
    return out.sort_values("cents_per_base_dollar").reset_index()


def yoy_inflation(annual: pd.DataFrame, category: str = "All items") -> pd.DataFrame:
    """Year-over-year % change in the annual average index."""
    s = annual[annual["category"] == category].set_index("year")["index"].sort_index()
    out = (100 * s.pct_change()).dropna().rename("yoy_pct").reset_index()
    out["above_fed_target"] = out["yoy_pct"] > FED_TARGET_PCT
    return out


# --------------------------------------------------------------------------- RPP
def parse_bea(path: Path) -> pd.DataFrame:
    """Regional Price Parities: one row per (state, year). U.S. = 100."""
    data = json.loads(Path(path).read_text())
    rows = []
    for obs in data["BEAAPI"]["Results"]["Data"]:
        fips = obs["GeoFips"]
        if fips == "00000":
            continue  # the U.S. row is 100 by definition
        value = str(obs["DataValue"]).replace(",", "")
        if value in ("(NA)", "(D)", ""):
            continue
        rows.append(
            {
                "fips": fips,
                "state": obs["GeoName"].replace(" *", "").strip(),
                "year": int(obs["TimePeriod"]),
                "rpp": float(value),
            }
        )
    return pd.DataFrame(rows).sort_values(["year", "rpp"], ascending=[True, False]).reset_index(drop=True)


def rpp_summary(rpp: pd.DataFrame) -> pd.DataFrame:
    """Latest RPP per state, how far $100 goes there, and the change since the first year."""
    first, last = rpp["year"].min(), rpp["year"].max()
    wide = rpp.pivot(index="state", columns="year", values="rpp")
    out = pd.DataFrame(
        {
            f"rpp_{first}": wide[first],
            f"rpp_{last}": wide[last],
        }
    )
    out["change_pts"] = out[f"rpp_{last}"] - out[f"rpp_{first}"]
    # $100 at national-average prices buys 100 / RPP * 100 dollars' worth locally
    out["value_of_100_usd"] = 100 * 100 / out[f"rpp_{last}"]
    return out.sort_values(f"rpp_{last}", ascending=False).reset_index()


def load_cached(raw_dir: Path = RAW_DIR) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    cpi_paths = sorted(raw_dir.glob("bls_cpi_*.json"))
    if not cpi_paths:
        raise SystemExit("No CPI data in data/raw. Run:  python -m money.fetch")
    monthly = parse_bls(cpi_paths)
    bea = raw_dir / "bea_sarpp_states.json"
    rpp = parse_bea(bea) if bea.exists() else None
    return monthly, rpp
