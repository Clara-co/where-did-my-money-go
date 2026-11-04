"""Tests run on small hand-built API responses in the same shape as the real ones."""

import json

import pandas as pd
import pytest

from money import __main__ as runner
from money import analysis
from money.fetch import CPI_SERIES, _year_windows


def bls_response(values: dict[str, dict[int, float]], missing=()) -> dict:
    """values: series_id -> {year: index}. Every month of a year gets the same value."""
    series = []
    for sid, by_year in values.items():
        data = []
        for year, v in by_year.items():
            for m in range(1, 13):
                val = "-" if (sid, year, m) in missing else str(v)
                data.append({"year": str(year), "period": f"M{m:02d}", "value": val})
            data.append({"year": str(year), "period": "M13", "value": "999"})  # must be ignored
        series.append({"seriesID": sid, "data": data})
    return {"status": "REQUEST_SUCCEEDED", "Results": {"series": series}}


def bea_response(rows: list[tuple[str, str, int, str]]) -> dict:
    return {"BEAAPI": {"Results": {"Data": [
        {"GeoFips": f, "GeoName": n, "TimePeriod": str(y), "DataValue": v} for f, n, y, v in rows
    ]}}}


@pytest.fixture
def raw_dir(tmp_path):
    # Shelter doubles; everything else rises 25%
    vals = {sid: {2015: 100.0, 2025: 125.0} for sid in CPI_SERIES}
    vals["CUUR0000SAH1"] = {2015: 100.0, 2025: 200.0}
    for y in range(2016, 2025):
        vals["CUUR0000SA0"][y] = 100.0 + 2.5 * (y - 2015)
    missing = {("CUUR0000SA0", 2025, 10)}
    (tmp_path / "bls_cpi_2015_2024.json").write_text(json.dumps(bls_response(vals, missing)))
    (tmp_path / "bea_sarpp_states.json").write_text(json.dumps(bea_response([
        ("00000", "United States", 2014, "100.000"), ("00000", "United States", 2024, "100.000"),
        ("15000", "Hawaii *", 2014, "118.0"), ("15000", "Hawaii *", 2024, "110.0"),
        ("28000", "Mississippi", 2014, "86.0"), ("28000", "Mississippi", 2024, "87.0"),
        ("06000", "California", 2014, "(NA)"), ("06000", "California", 2024, "112.0"),
    ])))
    return tmp_path


def test_year_windows_respect_ten_year_limit():
    assert _year_windows(2015, 2025) == [(2015, 2024), (2025, 2025)]
    assert _year_windows(2015, 2020) == [(2015, 2020)]


def test_parse_bls_skips_annual_rows_and_missing_months(raw_dir):
    monthly, _ = analysis.load_cached(raw_dir)
    assert (monthly["index"] != 999).all()
    annual = analysis.annual_average(monthly)
    row = annual[(annual["category"] == "All items") & (annual["year"] == 2025)].iloc[0]
    assert row["months"] == 11
    assert row["index"] == pytest.approx(125.0)


def test_purchasing_power_math(raw_dir):
    monthly, _ = analysis.load_cached(raw_dir)
    pp = analysis.purchasing_power(analysis.annual_average(monthly), 2015, 2025).set_index("category")
    assert pp.loc["Shelter", "cents_per_base_dollar"] == pytest.approx(50.0)
    assert pp.loc["Shelter", "price_change_pct"] == pytest.approx(100.0)
    assert pp.loc["All items", "cost_of_base_100"] == pytest.approx(125.0)
    assert pp.index[0] == "Shelter"  # sorted, biggest loss first


def test_yoy_flags_fed_target(raw_dir):
    monthly, _ = analysis.load_cached(raw_dir)
    yoy = analysis.yoy_inflation(analysis.annual_average(monthly)).set_index("year")
    assert yoy.loc[2016, "yoy_pct"] == pytest.approx(2.5)
    assert bool(yoy.loc[2016, "above_fed_target"])


def test_parse_bea_drops_us_row_and_missing_values(raw_dir):
    _, rpp = analysis.load_cached(raw_dir)
    assert "United States" not in set(rpp["state"])
    assert "Hawaii" in set(rpp["state"])  # footnote star stripped
    assert len(rpp) == 5  # California 2014 was (NA)


def test_rpp_summary(raw_dir):
    _, rpp = analysis.load_cached(raw_dir)
    s = analysis.rpp_summary(rpp).set_index("state")
    assert s.loc["Hawaii", "change_pts"] == pytest.approx(-8.0)
    assert s.loc["Mississippi", "value_of_100_usd"] == pytest.approx(100 * 100 / 87)


def test_full_run_writes_outputs(raw_dir, tmp_path):
    out = tmp_path / "out"
    runner.main(raw_dir=raw_dir, out=out)
    for f in ["purchasing_power.png", "inflation_yoy.png", "rpp_tile_map.png", "rpp_extremes.png"]:
        assert (out / "figures" / f).stat().st_size > 0
    summary = json.loads((out / "summary.json").read_text())
    assert summary["incomplete_years"] == [2025]
    assert "Note: annual averages for 2025" in (out / "RESULTS.md").read_text()
