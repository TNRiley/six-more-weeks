#!/usr/bin/env python3
"""Step 2: what the sky was doing on each Groundhog Day morning a prediction was made.

For every (forecaster, year) with a recorded shadow call since 1940, fetch ERA5 reanalysis for
Feb 2 at the forecaster's coordinates from Open-Meteo: hourly cloud cover, direct radiation and
sunshine duration. Requested in GMT and converted to local *standard* time with zoneinfo, because
Open-Meteo's timezone=auto labels February hours with the offset in force on the day you ask
(EDT in September), which silently shifts every morning by an hour.

One request per location-day costs one Open-Meteo call; ~1,600 calls, paced under the per-minute
limit. Cached in .cache/mornings/<slug>-<year>.json, so it resumes where it stopped.

    python fetch_mornings.py
"""
import json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache")
OUT = os.path.join(CACHE, "mornings")
os.makedirs(OUT, exist_ok=True)

URL = ("https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
       "&start_date={y}-02-02&end_date={y}-02-02"
       "&hourly=cloud_cover,direct_radiation,sunshine_duration&timezone=GMT")


def main():
    gh = json.load(open(os.path.join(CACHE, "groundhogs.json"), encoding="utf-8"))["groundhogs"]
    todo = []
    for g in gh:
        lat, lon = map(float, g["coordinates"].strip(", ").split(",")[:2])
        for p in g["predictions"]:
            if p["shadow"] is not None and p["year"] >= 1940:
                todo.append((g["slug"], p["year"], lat, lon))
    print(len(todo), "location-days")
    # optional sharding so several copies can run side by side: fetch_mornings.py 1 4
    if len(sys.argv) == 3:
        i, k = int(sys.argv[1]), int(sys.argv[2])
        todo = todo[i::k]
    done = 0
    for slug, y, lat, lon in todo:
        path = os.path.join(OUT, f"{slug}-{y}.json")
        if os.path.exists(path):
            continue
        for attempt in range(6):
            try:
                req = urllib.request.Request(URL.format(lat=lat, lon=lon, y=y),
                                             headers={"User-Agent": "six-more-weeks research script"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    open(path, "wb").write(r.read())
                break
            except urllib.error.HTTPError as e:
                wait = 65 if e.code == 429 else 5 * (attempt + 1)
                print(f"  {slug} {y}: HTTP {e.code}, waiting {wait}s")
                time.sleep(wait)
            except Exception as e:
                print(f"  {slug} {y}: {e}")
                time.sleep(5)
        done += 1
        if done % 100 == 0:
            print(done)
        time.sleep(0.1)


if __name__ == "__main__":
    main()
