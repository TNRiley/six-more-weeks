# 🦫 Six More Weeks

**Every Groundhog Day forecast on record, graded against the six weeks that followed. A groundhog that never came out of its burrow would win.**

→ **[Open it](https://tnriley.github.io/six-more-weeks/)**

1,442 Groundhog Day forecasts from 93 prognosticators — live groundhogs and marmots, ten taxidermied ones, people in suits, and also a lobster, an alligator, a largemouth bass, a golf club cover and a plastic flamingo — each graded against the literal six more weeks, February 3 to March 16, at the nearest long-running NOAA GHCN-Daily station. They were right 54.1% of the time. That beats a coin, but not a forecaster who stays in the burrow: the climate warms faster than a thirty-year normal can catch up, so a spring beats its own trailing normal 64% of the time, and 76% in the 2020s. Calling early spring every year would have scored 64%. Called at their own rates at random, the forecasters would have scored 51.7%, so their entire edge over chance is about 34 forecasts. Punxsutawney Phil calls winter 81% of the time and is right 43 times in 100. The only perfect record over five years belongs to Featherstone the Flamingo, a plastic lawn ornament in Massachusetts, which has never seen its shadow. The page carries two controls because one is not enough. The top of the table, an Alabama opossum right 13 times in 14, beats the best of 54 fair coins in 98% of replays, yet it sees its shadow in two years of fourteen in a place where spring is usually early, and calling at that rate at random would already score 70%. Matching every forecast since 1940 to ERA5 reanalysis of the sky over its burrow shows that someone really does look: shadows are called on 60% of sunny mornings and 29% of overcast ones. The taxidermied forecasters respond to the sky even more sharply than the live ones, so the handlers are the ones looking. The measurement they take is also useless: six weeks after a sunny Groundhog Day ran +0.75 °F warmer than after an overcast one, the opposite of the Candlemas rhyme, with an interval that straddles zero.

## Running it

One self-contained HTML file. No build step, no server, no network access at runtime — open `index.html` in a browser, or serve the directory with any static host.

```bash
python3 -m http.server 8000   # then visit http://localhost:8000
```

## Rebuilding it from scratch

[REBUILD.md](REBUILD.md) is written for an LLM with a shell and nothing else: the data sources and their quirks, the processing decisions, the page's structure and interactions, and a table of expected values to check the result against.

## Source

The full build pipeline is in [`src/`](src/), with a README describing how to regenerate the page from scratch.

## Data

- **[groundhog-day.com API — prognosticators and their recorded shadow calls, each record citing its own source](https://groundhog-day.com/api/v1/groundhogs)** — public API; forecast records are compiled facts, each forecaster links its original source
- **[NOAA NCEI GHCN-Daily station records (TMAX, TMIN) via the NCEI Access Data Service](https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries)** — US Government public domain
- **[ERA5 reanalysis (hourly cloud cover and sunshine duration) via the Open-Meteo Historical Weather API](https://archive-api.open-meteo.com/v1/archive)** — CC-BY-4.0 (Open-Meteo); ERA5 contains modified Copernicus Climate Change Service information

Every figure on the page is computed from the data shipped with it. Check the page's own methods panel for how each number is derived and where it should not be pushed.

## Built with

python 3 stdlib, nearest-complete-station selection, coin-field Monte Carlo, year-block bootstrap, vanilla JS, canvas, inline SVG.

## Licence

Code is MIT (see [LICENSE](LICENSE)). Data keeps the licence of its source, listed above.

---

Part of [Quick Projects](https://github.com/TNRiley/quick-projects) — one self-contained thing, built in one session. First published 2026-09-16.
