# Pipeline

Run in order from this directory with Python 3.9+ (stdlib only; `python`, not `python3`, on Windows).

```bash
python fetch_stations.py        # forecasts + GHCN station lists + one CSV per chosen station (~290 MB in .cache/)
python fetch_mornings.py        # ERA5 Feb 2 skies, one call per forecaster-year; shard with: fetch_mornings.py 0 4 … 3 4
python build_payload.py         # grades everything, writes payload.json and prints headline figures
python inject.py                # splices payload into template.html → ../index.html, wraps for Pages, adds catalog link
```

Everything fetched is cached in `.cache/` and every step resumes. `payload.json` and `.cache/` are
not committed. See `../REBUILD.md` for the decisions and the expected values.
