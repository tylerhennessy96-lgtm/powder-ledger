# Powder Ledger

A snowfall tracker for seven Rocky Mountain resorts: Winter Park, Aspen / Snowmass,
Snowbird / Alta, Taos, Jackson Hole, Big Sky and Wolf Creek. It shows this season to date
against each of the last ten seasons, their average, and the biggest and leanest years.

## Files

- `artifact.html` — the page source (styles and script inline), written as a fragment for publishing as a Claude artifact. Edit this one.
- `index.html` — the complete page GitHub Pages serves, generated from `artifact.html` by `scripts/build_site.sh`. It loads `data.json` from the same folder.
- `data.json` — processed season data, one entry per resort.
- `scripts/refresh.sh` — downloads daily readings and rebuilds `data.json`.
- `scripts/build_data.py` — turns the raw readings into `data.json`; the resort-to-station list lives here.
- `reported.json` — the season total each resort reports on its own snow report, where it publishes one.
- `scripts/fetch_reported.py` — reads those resort reports and rebuilds `reported.json`.
- `scripts/build_site.sh` — rebuilds `index.html` after a change to `artifact.html`.

## Data

Daily snow depth and snow water equivalent from USDA NRCS SNOTEL stations
(AWDB REST API at `wcc.sc.egov.usda.gov`). Snowfall is estimated as the sum of each
day's rise in snow depth, so totals run well below resort-reported figures.
A season is October 1 to May 31.

Resort-reported totals come from each resort's own snow report or the public feed behind it
(Snowbird, Alta, Taos, Jackson Hole, Big Sky, Aspen Snowmass, Wolf Creek). Winter Park is linked
but not read automatically, and a resort that has not published a season total shows a dash.

## Refresh the data

```bash
./scripts/refresh.sh
```

```bash
python3 scripts/fetch_reported.py reported.json
```

A GitHub Actions workflow runs both twice a day from October through June and commits the results.

Needs `curl` and Python 3, and network access to `wcc.sc.egov.usda.gov`.

## View locally

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000/.
