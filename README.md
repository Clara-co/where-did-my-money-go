# Where Did My Money Go?

U.S. inflation by spending category, 2015 to 2025, and the cost of living across the 50 states and DC.

This is the reproducible version of my [data storytelling project](https://clara-co.github.io/projects/where-did-my-money-go-report.pdf). The original was built from Excel downloads. This repo pulls the same government series directly from the BLS and BEA APIs, caches the raw responses, and rebuilds every number and chart with one command.

**Results:** `outputs/RESULTS.md`, created when you run the pipeline (see [Run it](#run-it)). The analysis writes that page itself, so every figure on it comes from the data in `data/raw/`.

## Questions

1. **How far does a 2015 dollar go in 2025, by category?** Is housing really the worst?
2. **When did inflation spike, and is it back to the Fed's 2% target?**
3. **How much does where you live change what a dollar buys?**

## Data

| Source | Series | Years |
|---|---|---|
| [BLS CPI-U](https://www.bls.gov/cpi/), U.S. city average, not seasonally adjusted | All items `CUUR0000SA0`, Shelter `SAH1`, Transportation `SAT`, Motor fuel `SETB`, Food `SAF1`, Medical care `SAM`, Recreation `SAR` | 2015 to 2025, monthly |
| [BEA Regional Price Parities](https://www.bea.gov/data/prices-inflation/regional-price-parities-state-and-metro-area), table SARPP line 1 (all items) | 50 states + DC | 2014 to 2024, annual |

## Method

- **Annual averages** are the mean of the monthly index values. The pipeline counts how many months go into each year instead of assuming 12. This matters for 2025: [BLS did not collect October 2025 CPI data](https://www.bls.gov/cpi/additional-resources/2025-federal-government-shutdown-impact-cpi.htm) during the federal shutdown, so the 2025 average uses 11 months. `RESULTS.md` flags this automatically.
- **Purchasing power** of a base-year dollar is `CPI(base) / CPI(end)`. If shelter prices rise 47%, a 2015 shelter dollar buys 1 / 1.47 ≈ 68¢.
- **Inflation** is the year-over-year % change in the annual average index for all items, compared with the Fed's 2% target.
- **Cost of living:** an RPP of 110 means prices are 10% above the national average, so $100 there buys what $100 / 1.10 ≈ $91 buys at average prices.

## Project layout

```
src/money/
  fetch.py      BLS + BEA API clients; splits BLS requests into 10-year windows; caches JSON to data/raw/
  analysis.py   parse responses, annual averages with month counts, purchasing power, YoY, RPP summary
  charts.py     matplotlib charts, including a 51-state tile-grid map
  __main__.py   run the analysis, write outputs/ and the generated RESULTS.md
tests/          7 tests on hand-built API responses (parsing, missing months, the math, a full run)
```

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

export BEA_API_KEY=...        # free: https://apps.bea.gov/api/signup/
export BLS_API_KEY=...        # optional: https://data.bls.gov/registrationEngine/

python -m money.fetch         # downloads to data/raw/ (commit these so results are reproducible)
python -m money               # writes outputs/tables, outputs/figures, outputs/RESULTS.md
pytest
```

The BLS API works without a key but limits each request to 10 years, so `fetch.py` splits 2015 to 2025 into two requests. Without `BEA_API_KEY`, the CPI half still runs and the state section is skipped.

## Limitations

- National CPI is an average for urban consumers. Your own inflation depends on what you buy and where you live.
- RPPs compare price *levels* across states in one year. They are not a measure of how fast prices rose in each state.
- CPI shelter measures rent and owners' equivalent rent, not home purchase prices.

**Tools:** Python, pandas, matplotlib, BLS and BEA APIs, pytest.
