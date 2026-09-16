#!/usr/bin/env python3
"""Step 1: pick a GHCN-Daily weather station for every prognosticator and download its record.

For each forecaster in groundhog-day.com's list, the years we need run from 30 years before its
first recorded prediction (the trailing-normal baseline) through 2026, never earlier than 1900.
Candidate stations are the ten nearest within 100 km whose TMAX and TMIN inventories overlap that
span by at least 70%. Each is downloaded and scored by the share of needed years whose six-week
window (Feb 3 - Mar 16) has both readings on 38 of 42 days; the first to reach 90% wins, otherwise
the best seen. No splicing between stations - a year a station cannot grade stays ungraded.
Records land in .cache/ghcnd/<station>.csv.

    python fetch_stations.py
"""
import json, math, os, csv, io, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache")
GHCN = os.path.join(CACHE, "ghcnd")
os.makedirs(GHCN, exist_ok=True)

GROUNDHOGS_URL = "https://groundhog-day.com/api/v1/groundhogs"
BASE = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/"
DATA = ("https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries"
        "&stations={sid}&startDate=1900-01-01&endDate=2026-03-31&dataTypes=TMAX,TMIN&units=metric")
RADIUS_KM = 100
LAST_NEEDED = 2026


def get(url, path, timeout=300):
    if not os.path.exists(path):
        req = urllib.request.Request(url, headers={"User-Agent": "six-more-weeks research script"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
        open(path, "wb").write(data)
    return path


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def window_days(year):
    """Feb 3 .. Mar 16 inclusive: the six weeks after Groundhog Day (42 days)."""
    import datetime as dt
    d0 = dt.date(year, 2, 3)
    return [(d0 + dt.timedelta(i)).isoformat() for i in range(42)]


def completeness(path, years):
    tmax, tmin = {}, {}
    for row in csv.DictReader(open(path, encoding="utf-8")):
        if row.get("TMAX", "").strip():
            tmax[row["DATE"]] = 1
        if row.get("TMIN", "").strip():
            tmin[row["DATE"]] = 1
    good = 0
    for y in years:
        n = sum(1 for d in window_days(y) if d in tmax and d in tmin)
        good += n >= 38
    return good / len(years)


def main():
    gh = json.load(open(get(GROUNDHOGS_URL, os.path.join(CACHE, "groundhogs.json")), encoding="utf-8"))["groundhogs"]
    get(BASE + "ghcnd-stations.txt", os.path.join(CACHE, "ghcnd-stations.txt"))
    get(BASE + "ghcnd-inventory.txt", os.path.join(CACHE, "ghcnd-inventory.txt"))

    span = {}
    for line in open(os.path.join(CACHE, "ghcnd-inventory.txt"), encoding="utf-8"):
        sid, lat, lon, el, y0, y1 = line.split()
        if el in ("TMAX", "TMIN"):
            s = span.setdefault(sid, {"lat": float(lat), "lon": float(lon)})
            s[el] = (int(y0), int(y1))
    names = {}
    for line in open(os.path.join(CACHE, "ghcnd-stations.txt"), encoding="utf-8"):
        names[line[:11]] = line[41:71].strip()
    def overlap(s, y0, y1):
        a = max(s["TMAX"][0], s["TMIN"][0], y0); b = min(s["TMAX"][1], s["TMIN"][1], y1)
        return max(0, b - a + 1) / (y1 - y0 + 1)
    both = {sid: s for sid, s in span.items() if "TMAX" in s and "TMIN" in s}

    chosen = {}
    for g in gh:
        lat, lon = map(float, g["coordinates"].strip(", ").split(",")[:2])
        pred = [p["year"] for p in g["predictions"] if p["shadow"] is not None]
        if not pred:
            chosen[g["slug"]] = None
            continue
        y0 = max(1900, min(pred) - 30)
        years = list(range(y0, LAST_NEEDED + 1))
        cands = sorted(((km((lat, lon), (s["lat"], s["lon"])), sid) for sid, s in both.items()
                        if abs(s["lat"] - lat) < 1.2 and abs(s["lon"] - lon) < 1.8
                        and overlap(s, y0, LAST_NEEDED) >= 0.7))
        cands = [c for c in cands if c[0] <= RADIUS_KM][:10]
        pick, best = None, None
        for dist, sid in cands:
            path = os.path.join(GHCN, sid + ".csv")
            try:
                get(DATA.format(sid=sid), path)
            except Exception as e:
                print("  fetch failed", sid, e)
                time.sleep(2)
                continue
            c = completeness(path, years)
            rec = {"station": sid, "name": names.get(sid, ""), "km": round(dist, 1), "complete": round(c, 3), "from": y0}
            if best is None or c > best["complete"]:
                best = rec
            if c >= 0.9:
                pick = rec
                break
        pick = pick or best
        chosen[g["slug"]] = pick
        print(g["slug"], pick)
    json.dump(chosen, open(os.path.join(CACHE, "stations_chosen.json"), "w", encoding="utf-8", newline="\n"), indent=1)


if __name__ == "__main__":
    main()
