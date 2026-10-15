# ReflexDB Emerging Intelligence — MVP 0.1

A runnable demonstration of context-aware network degradation detection, emerging geographic patterns, and an operational dashboard.

**Current status:** synthetic rectangular grid (not real H3); no production StarRocks connector or durable processing yet. See docs/ARCHITECTURE.md.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
# Visit http://127.0.0.1:8000
pytest -q
```

CSV mode: `python app.py --csv data.csv`. Required columns: `hour_ts,market_id,h3_id,x,y,technology,throughput,sinr,harq,prb_util,sample_count,distinct_imsis`. Coordinates x/y are **demo grid coordinates only**; do not interpret clustering as true H3 geography. Use at least 72 distinct hourly periods, ideally 6+ weeks.

## Components
- `reflexdb/engine.py`: as-of baselines, directional residuals, EWMA/CUSUM, grid connected components, episode matching
- `app.py`: FastAPI operational API
- `web/index.html`: dashboard
- `tests/test_engine.py`: deterministic pipeline, no future leakage, output smoke tests
- `sql/starrocks_features.sql`: illustrative SQL
- `docs/ARCHITECTURE.md`: implementation scope and migration

## Limitations
- Baselines are frozen at the holdout cutoff, not incrementally updated.
- Hour-of-week baselines fall back to daypart/technology peers for sparse history.
- Thresholds and episode scores are illustrative and uncalibrated.
- Episode lineage is simple one-hour overlap; no durable state or late-data replay.
- Summed per-cell distinct IMSIs are an exposure proxy, **not deduplicated impacted users**.
- No real H3 neighbor graph, StarRocks connection, authentication, NIDL invocation, or network control.
