# Rebuilding Six More Weeks

Written for an LLM with a shell and nothing else.

## What this is

A single self-contained HTML page that grades every Groundhog Day forecast on record against
the weather that followed. The finding it exists to show is about controls, not groundhogs.
The forecasters are right 54.1% of the time, which beats a coin. But in a warming climate a
spring beats its own thirty-year trailing normal 64% of the time, so a forecaster that never
saw its shadow would have scored 64%. Against chance at each forecaster's *own* call rate, the
whole field's edge is about 34 forecasts out of 1,442. Two further tests use the sky on each
Feb 2 morning. Handlers do call shadows more on sunny mornings (60% against 29%), and the
taxidermied forecasters track the sky more sharply than the live ones. The sky on Feb 2 does
not predict the next six weeks.

## Data sources

1. **Forecasts**: `https://groundhog-day.com/api/v1/groundhogs` (one JSON, ~180 KB).
   93 forecasters. Each has `coordinates` as a `"lat,lon"` string, `type` (free text from
   "Groundhog" to "Groundhog golf club cover"), and `predictions[]` of `{year, shadow, details}`.
   - `shadow` is `1`, `0` or `null` ("No Record"). Drop nulls: 1,643 calls remain.
   - **Buckeye Chuck's coordinates have a trailing comma** (`"40.61,-83.13,"`). Strip `", "`
     before splitting, or the float parse dies halfway through the run.
   - Phil's record starts in 1887. Most forecasters start after 2000.
2. **Temperatures**: GHCN-Daily via the NCEI Access Data Service, one CSV per station:
   `https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations=<ID>&startDate=1900-01-01&endDate=2026-03-31&dataTypes=TMAX,TMIN&units=metric`.
   Station metadata comes from `ghcnd-stations.txt` (11 MB) and `ghcnd-inventory.txt` (36 MB)
   under `https://www.ncei.noaa.gov/pub/data/ghcn/daily/`. The inventory gives only first and
   last years per element, not gaps. Completeness has to be measured on the download.
3. **Morning sky**: Open-Meteo historical API, one call per forecaster-year since 1940 (1,588 calls):
   `https://archive-api.open-meteo.com/v1/archive?latitude=..&longitude=..&start_date=Y-02-02&end_date=Y-02-02&hourly=cloud_cover,direct_radiation,sunshine_duration&timezone=GMT`.
   - **Do not use `timezone=auto`.** It stamps February hours with the UTC offset in force on the
     day you ask (EDT in September), shifting every morning by an hour. Request GMT and convert
     with `zoneinfo`, looking up each location's IANA zone once (`src/.cache/tz.json`).
   - Multi-year ranges are billed as many calls (weight grows with days requested). One day per
     request costs one call. The free tier allows ~600/min, and four sharded workers finish in
     about ten minutes. Expect a few `WinError 10054` resets; the fetcher retries.

## Processing

- **Station choice** (`src/fetch_stations.py`). Needed years run from 30 years before a
  forecaster's first call through 2026, never before 1900. Candidates are the 10 nearest stations
  within 100 km whose TMAX and TMIN inventories overlap that span by at least 70%. Download
  nearest-first and score each by the share of needed years whose window has both readings on
  38 of 42 days. Take the first at 90% or better, otherwise the best seen. No splicing.
  Every forecaster gets a station, though Wiarton Willie's (Durham, Ontario) is only 44% complete.
- **Outcome**: "six more weeks" literally, Feb 3 through Mar 16 (42 days). Daily mean =
  (TMAX+TMIN)/2. A year needs 38 days.
- **Normals**: *trailing* = mean of the previous 30 windows, needing at least 20 (headline);
  *fixed* = the station's 1991–2020 mean, needing at least 20 years. Early spring = window mean >
  normal, and a tie counts as winter. Correct = (shadow and not early) or (no shadow and early).
- **Controls**:
  - never/always sees its shadow, on the same graded rows;
  - *own-rate chance* per forecaster, `s·(1−e) + (1−s)·e`, where s = its shadow rate and e = its
    early-spring rate. **This is the control that matters.** A plain coin makes any forecaster
    who rarely sees a shadow look skilled, because early springs are the majority outcome;
  - a *coin field*: each of the 54 forecasters with 10 or more graded years replayed with fair
    coins, 20,000 times, seed 20260202. Record the 5/50/95% points of the best, median and worst
    coin, and P(best coin ≥ top real score).
- **Kinds**: taxidermied* → stuffed; "person in…" → costume; plush/puppet/statue/mural/
  plastic/animatronic/golf club → object; groundhog, presumed groundhog or any marmot → live;
  everything else → other animals.
- **Sun at the burrow**: sunshine_duration summed over hours stamped 08 and 09 local standard
  time (each stamp is the hour ending then, so it covers 07:00–09:00) is at least 30 minutes.
- **Rhyme test**: six-week departure from the trailing normal, sunny against overcast mornings.
  The interval comes from a bootstrap that resamples **whole years** (4,000 draws), because
  neighbouring burrows share one year's weather.

## Methodological trap hit during the build

The first draft of the page argued that the fixed 1991–2020 normal was the biased yardstick and
that the trailing normal fixed it, so under the trailing normal "always spring" should score
about 50%. **Wrong.** Under the trailing normal early springs are 64.2% of graded rows (fixed:
61.8%). A trailing mean lags any trend, so it is biased the same way. The headline control is
therefore own-rate chance, not a coin, and not "the right normal".

## The page

`src/template.html` holds a `__DATA__` placeholder. `src/inject.py` splices in
`src/payload.json` (escaping `</`), then runs `catalog/tools/wrap_for_pages.py` and
`add_catalog_link.py` (pass `--no-finish` to keep an Artifact-style fragment).

- Palette: frost ground `#E7ECEF`, burrow ink `#1E1B18`, winter indigo `#46558A`, spring green
  `#57843A`, sunrise gold `#C08A2E` (only for the sun and the coin band). Full dark theme.
- Type: Gloock (display), Instrument Sans (body), IBM Plex Mono (figures and labels).
- Hero: a canvas dawn with a burrow and a groundhog in front of a top hat. A cloud bank crosses
  a low sun and the shadow fades when the sun is covered. Reduced motion gives a static frame.
- Verdict row: 54% overall · 64% never-sees-shadow · Phil 43/100 · Featherstone 8/8.
- Scoreboard: one row per forecaster on a shared 0–100% scale showing the dot (colour = mostly
  shadow or mostly not), Wilson 95% whisker, dashed coin line, gold best-coin band and a black
  own-rate-chance tick. Two hatched ghost rows (never/always). Toggles: normal (trailing/fixed),
  kind chips, sort, "10+ graded years" (on by default), search. A row expands to a per-year bar
  strip of departure from normal, coloured by the call, faded with × when wrong. Phil opens by default.
- Three findings, each a chart plus prose computed from the payload: decades (early share ×2
  normals, shadow share, accuracy), the ritual (shadow rate sunny/overcast by kind, with
  intervals), the rhyme (sunny, overcast and gap with the year-bootstrap interval). Then methods.

## Verification table

| check | expected |
|---|---|
| forecasters / calls with a shadow value | 93 / 1,643 |
| graded, trailing normal | 1,442 rows, 780 right, 54.09% (Wilson 51.5–56.6%) |
| graded, fixed normal | 1,389 rows, 729 right, 52.48% |
| early-spring share, trailing / fixed | 64.22% / 61.84% |
| early share in the 2020s, trailing / fixed | 76% / 77% (482 rows each) |
| shadow share of graded calls | 48.82% |
| own-rate chance, pooled | 51.74% |
| forecasters with 10+ graded years | 54 |
| best-coin 5/50/95% | 70.0% / 78.6% / 90.0% |
| top with 10+ years | Sand Mountain Sam (opossum, Alabama) 13/14, own-rate chance 70.4%, P(best coin ≥) ≈ 1.6% |
| Punxsutawney Phil | 43/100, 81 shadows, 58 early springs, station USC00363028 FRANKLIN 89.5 km |
| Featherstone the Flamingo | 8/8, 0 shadows, WORCESTER USW00094746 |
| Potomac Phil (taxidermied, DC) | 5/15, Reagan National USW00013743, 7.0 km |
| Staten Island Chuck | 23/31, Newark USW00014734 |
| Phil 2026 row | shadow, six weeks 0.87 °C, trailing normal −0.96 °C, 73 sun-minutes |
| shadow rate, sunny / overcast mornings | 582/966 = 60.2% / 181/622 = 29.1% |
| taxidermied, sunny / overcast | 123/162 / 34/72 |
| rhyme gap, sunny − overcast | +0.75 °F, 95% year-bootstrap −0.38 to +2.18 °F, over 86 years |

Numbers shift slightly if groundhog-day.com adds or corrects records, or if NCEI backfills a station.

## What the page must say about itself

- Nearby forecasters share weather, so pooled intervals are too narrow.
- Stations are not homogenised, and Phil's is 89.5 km away.
- ERA5 is a ~25 km grid model, not an observer at the burrow, and some ceremonies are held indoors.
- Every forecaster has handlers, so every call measures people.
- None of this can separate luck from skill for any single forecaster.
