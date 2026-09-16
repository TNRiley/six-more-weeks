#!/usr/bin/env python3
"""Step 3: grade every forecast and write payload.json for the page.

Outcome. "Six more weeks" is taken literally: the 42 days Feb 3 - Mar 16. Each day's mean is
(TMAX+TMIN)/2 at the forecaster's chosen GHCN station; a year needs 38 of 42 days. The spring was
"early" if that six-week mean beat normal. Two normals are carried, because the answer depends on
which one you pick and that dependence is the point of one section of the page:

  trailing  the mean of the previous 30 six-week windows (at least 20 present) - what "normal"
            meant to someone standing at the burrow that morning. Headline scoring uses this.
  fixed     the 1991-2020 climate normal (at least 20 years present) - what a lazy scorer uses,
            and what a warming climate turns into a thumb on the scale.

Correct = shadow and not early, or no shadow and early. A tie with the normal is not early.

Controls, all graded on exactly the same station-years as the real forecasts:
  coins     every forecaster's graded years replayed with fair coins, 20,000 times, to give the
            accuracy the best / median / worst of a field of coins would reach by luck alone
  spring    a forecaster who never sees a shadow
  winter    a forecaster who always does

Mornings. ERA5 hourly for Feb 2 at the forecaster's coordinates, converted to local standard
time. "Sun at the burrow" = at least 30 minutes of sunshine between 07:00 and 09:00 local.

    python build_payload.py        # writes ../.cache-free payload.json beside this script
"""
import csv, datetime as dt, json, math, os, random, statistics, zoneinfo
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache")
random.seed(20260202)


def wilson(k, n, z=1.96):
    if n == 0:
        return (0, 0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def binom_two_sided(k, n):
    """Exact two-sided binomial test against p = 0.5."""
    if n == 0:
        return 1.0
    pmf = [math.comb(n, i) / 2 ** n for i in range(n + 1)]
    return min(1.0, sum(q for q in pmf if q <= pmf[k] * (1 + 1e-9)))


def windows(station):
    by = defaultdict(list)
    path = os.path.join(CACHE, "ghcnd", station + ".csv")
    for row in csv.DictReader(open(path, encoding="utf-8")):
        mx, mn = row.get("TMAX", "").strip(), row.get("TMIN", "").strip()
        if not mx or not mn:
            continue
        d = dt.date.fromisoformat(row["DATE"])
        start = dt.date(d.year, 2, 3)
        if 0 <= (d - start).days < 42:
            by[d.year].append((float(mx) + float(mn)) / 2)
    return {y: sum(v) / len(v) for y, v in by.items() if len(v) >= 38}


def normals(W):
    trail, fixed = {}, None
    fx = [W[y] for y in range(1991, 2021) if y in W]
    if len(fx) >= 20:
        fixed = sum(fx) / len(fx)
    for y in W:
        prev = [W[p] for p in range(y - 30, y) if p in W]
        if len(prev) >= 20:
            trail[y] = sum(prev) / len(prev)
    return trail, fixed


def morning(slug, year, lat, lon, tzcache={}):
    path = os.path.join(CACHE, "mornings", f"{slug}-{year}.json")
    if not os.path.exists(path):
        return None
    d = json.load(open(path, encoding="utf-8"))
    key = (round(lat, 1), round(lon, 1))
    if key not in tzcache:
        tzcache[key] = tz_for(lat, lon)
    tz = tzcache[key]
    h = d["hourly"]
    sun = cloud = 0.0
    nc = 0
    for i, t in enumerate(h["time"]):
        u = dt.datetime.fromisoformat(t).replace(tzinfo=dt.timezone.utc).astimezone(tz)
        # sunshine_duration is the seconds of sun in the hour *ending* at the stamp
        if 8 <= u.hour <= 9:
            sun += h["sunshine_duration"][i] or 0
        if 7 <= u.hour <= 9 and h["cloud_cover"][i] is not None:
            cloud += h["cloud_cover"][i]; nc += 1
    return {"sunMin": round(sun / 60), "cloud": round(cloud / nc) if nc else None}


def tz_for(lat, lon):
    """IANA zone for a location, looked up once from Open-Meteo and cached in .cache/tz.json."""
    path = os.path.join(CACHE, "tz.json")
    tab = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    key = f"{lat:.4f},{lon:.4f}"
    if key not in tab:
        import urllib.request
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
               "&timezone=auto&daily=sunrise&forecast_days=1")
        with urllib.request.urlopen(url, timeout=60) as r:
            tab[key] = json.load(r)["timezone"]
        json.dump(tab, open(path, "w", encoding="utf-8", newline="\n"), indent=1)
    return zoneinfo.ZoneInfo(tab[key])


def kind(t):
    """Five groups from groundhog-day.com's free-text type, which runs from "Groundhog" to
    "Groundhog golf club cover" and "Atlantic lobster"."""
    t = t.lower()
    if t.startswith("taxidermied"):
        return "stuffed"
    if t.startswith("person in"):
        return "costume"
    if any(w in t for w in ("plush", "puppet", "statue", "mural", "plastic", "animatronic", "golf club")):
        return "object"
    if t in ("groundhog", "presumed groundhog") or "marmot" in t:
        return "live"
    return "other"


def main():
    gh = json.load(open(os.path.join(CACHE, "groundhogs.json"), encoding="utf-8"))["groundhogs"]
    stations = json.load(open(os.path.join(CACHE, "stations_chosen.json"), encoding="utf-8"))

    out, pooled = [], []
    for g in gh:
        lat, lon = map(float, g["coordinates"].strip(", ").split(",")[:2])
        st = stations.get(g["slug"])
        W, trail, fixed = {}, {}, None
        if st:
            W = windows(st["station"])
            trail, fixed = normals(W)
        years = []
        for p in sorted(g["predictions"], key=lambda p: p["year"]):
            if p["shadow"] is None:
                continue
            y = p["year"]
            rec = {"y": y, "s": p["shadow"]}
            if y in W:
                rec["t"] = round(W[y], 2)
                if y in trail:
                    rec["nt"] = round(trail[y], 2)
                if fixed is not None:
                    rec["nf"] = round(fixed, 2)
            m = morning(g["slug"], y, lat, lon) if y >= 1940 else None
            if m:
                rec["sun"] = m["sunMin"]; rec["cloud"] = m["cloud"]
            years.append(rec)
            pooled.append((g["slug"], rec))
        out.append({
            "slug": g["slug"], "name": g["name"], "short": g["shortname"], "city": g["city"],
            "region": g["region"], "country": g["country"], "lat": lat, "lon": lon,
            "type": g["type"], "kind": kind(g["type"]), "active": g["active"],
            "desc": g["description"], "src": g["source"],
            "station": st, "years": years,
        })

    # ── grading ────────────────────────────────────────────────────────────
    def graded(f, base):
        key = "nt" if base == "trailing" else "nf"
        rows = []
        for r in f["years"]:
            if "t" in r and key in r:
                early = r["t"] > r[key]
                rows.append((r, early, (r["s"] == 1) != early))
        return rows

    summary = {}
    for base in ("trailing", "fixed"):
        board, allrows = [], []
        for f in out:
            rows = graded(f, base)
            if not rows:
                continue
            k, n = sum(c for _, _, c in rows), len(rows)
            early = sum(e for _, e, _ in rows)
            shadow = sum(r["s"] for r, _, _ in rows)
            lo, hi = wilson(k, n)
            # what this forecaster would score calling winter at its own rate, but at random
            sh = shadow / n
            chance = sh * (1 - early / n) + (1 - sh) * (early / n)
            board.append({"slug": f["slug"], "n": n, "k": k, "acc": k / n, "lo": lo, "hi": hi, "chance": chance,
                          "p": binom_two_sided(k, n), "early": early, "shadows": shadow,
                          "spring": early / n, "winter": 1 - early / n})
            allrows += [(f, r, e, c) for r, e, c in rows]
        ns = [b["n"] for b in board]
        # a field of coins with exactly these sample sizes
        best, med, worst, above = [], [], [], []
        eligible = [n for n in ns if n >= 10]
        for _ in range(20000):
            accs = sorted(sum(random.random() < 0.5 for _ in range(n)) / n for n in eligible)
            best.append(accs[-1]); worst.append(accs[0]); med.append(accs[len(accs) // 2])
        best.sort(); worst.sort(); med.sort()
        top = max((b for b in board if b["n"] >= 10), key=lambda b: (b["acc"], b["n"]))
        p_best = sum(x >= top["acc"] - 1e-12 for x in best) / len(best)
        q = lambda a, x: a[int(x * (len(a) - 1))]
        K = sum(c for *_, c in allrows); N = len(allrows)
        E = sum(e for _, _, e, _ in allrows)
        S = sum(r["s"] for _, r, _, _ in allrows)
        by_kind = defaultdict(lambda: [0, 0])
        for f, r, e, c in allrows:
            by_kind[f["kind"]][0] += c; by_kind[f["kind"]][1] += 1
        by_decade = defaultdict(lambda: [0, 0, 0, 0])   # hits, n, early, shadows
        for f, r, e, c in allrows:
            d = by_decade[r["y"] // 10 * 10]
            d[0] += c; d[1] += 1; d[2] += e; d[3] += r["s"]
        summary[base] = {
            "board": board, "N": N, "K": K, "acc": K / N, "ci": wilson(K, N), "p": binom_two_sided(K, N),
            "earlyShare": E / N, "shadowShare": S / N,
            "alwaysSpring": E / N, "alwaysWinter": 1 - E / N,
            "chance": sum(b["chance"] * b["n"] for b in board) / N,
            "coins": {"eligibleN": len(eligible), "minN": 10, "top": top["slug"], "pBestAtLeastTop": p_best,
                      "best": [q(best, .05), q(best, .5), q(best, .95)],
                      "median": [q(med, .05), q(med, .5), q(med, .95)],
                      "worst": [q(worst, .05), q(worst, .5), q(worst, .95)]},
            "byKind": {k: {"k": v[0], "n": v[1], "acc": v[0] / v[1], "ci": wilson(*v)} for k, v in by_kind.items()},
            "byDecade": {str(k): {"k": v[0], "n": v[1], "acc": v[0] / v[1], "early": v[2] / v[1], "shadow": v[3] / v[1]}
                         for k, v in sorted(by_decade.items())},
        }

    # ── mornings: do they look, and is the rhyme right? ──────────────────────
    look = defaultdict(lambda: {"sunny": [0, 0], "dull": [0, 0]})
    rhyme = {"sunny": [], "dull": []}
    rhyme_years = defaultdict(lambda: {"sunny": [], "dull": []})
    for f in out:
        for r in f["years"]:
            if "sun" not in r:
                continue
            sunny = r["sun"] >= 30
            cell = look[f["kind"]]["sunny" if sunny else "dull"]
            cell[0] += r["s"]; cell[1] += 1
            cell = look["all"]["sunny" if sunny else "dull"]
            cell[0] += r["s"]; cell[1] += 1
            if "t" in r and "nt" in r:
                a = r["t"] - r["nt"]
                rhyme["sunny" if sunny else "dull"].append(a)
                rhyme_years[r["y"]]["sunny" if sunny else "dull"].append(a)
    # bootstrap the sunny-minus-dull anomaly gap by resampling whole years, because
    # neighbouring burrows share one year's weather and are not independent draws
    ys = [y for y in rhyme_years]
    gaps = []
    for _ in range(4000):
        s, d = [], []
        for y in random.choices(ys, k=len(ys)):
            s += rhyme_years[y]["sunny"]; d += rhyme_years[y]["dull"]
        if s and d:
            gaps.append(statistics.fmean(s) - statistics.fmean(d))
    gaps.sort()
    mornings = {
        "look": {k: {kk: {"shadows": vv[0], "n": vv[1]} for kk, vv in v.items()} for k, v in look.items()},
        "rhyme": {"sunnyN": len(rhyme["sunny"]), "dullN": len(rhyme["dull"]),
                  "sunnyMean": statistics.fmean(rhyme["sunny"]) if rhyme["sunny"] else None,
                  "dullMean": statistics.fmean(rhyme["dull"]) if rhyme["dull"] else None,
                  "gapCI": [gaps[int(.025 * len(gaps))], gaps[int(.975 * len(gaps))]] if gaps else None,
                  "years": len(ys)},
    }

    payload = {"built": dt.date.today().isoformat(), "forecasters": out, "summary": summary, "mornings": mornings}
    json.dump(payload, open(os.path.join(HERE, "payload.json"), "w", encoding="utf-8", newline="\n"),
              ensure_ascii=False, separators=(",", ":"))
    t = summary["trailing"]; fx = summary["fixed"]
    print(f"trailing: {t['K']}/{t['N']} = {t['acc']:.3f}  early share {t['earlyShare']:.3f}  shadow share {t['shadowShare']:.3f}")
    print(f"fixed:    {fx['K']}/{fx['N']} = {fx['acc']:.3f}  early share {fx['earlyShare']:.3f}")
    print("coins best", [round(x, 3) for x in t["coins"]["best"]], "p(best coin >= top)", t["coins"]["pBestAtLeastTop"], t["coins"]["top"], "chance", round(t["chance"], 3))
    top = sorted([b for b in t["board"] if b["n"] >= 10], key=lambda b: -b["acc"])[:5]
    for b in top:
        print("  ", b["slug"], b["k"], b["n"], round(b["acc"], 3), round(b["p"], 3))
    print("by kind", {k: (v["k"], v["n"], round(v["acc"], 3)) for k, v in t["byKind"].items()})
    print("look", json.dumps(mornings["look"]["all"]), "rhyme", json.dumps(mornings["rhyme"]))


if __name__ == "__main__":
    main()
