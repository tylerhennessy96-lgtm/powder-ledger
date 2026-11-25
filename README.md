# Powder Ledger

A snowfall tracker for seven Rocky Mountain resorts: Winter Park, Aspen / Snowmass,
Snowbird / Alta, Taos, Jackson Hole, Big Sky and Wolf Creek. It shows this season to date
against each of the last ten seasons, their average, and the biggest and leanest years.

## Files

- `index.html` — the page (styles and script inline). It loads `data.json` from the same folder.
- `data.json` — processed season data, one entry per resort.
- `scripts/refresh.sh` — downloads daily readings and rebuilds `data.json`.
- `scripts/build_data.py` — turns the raw readings into `data.json`; the resort-to-station list lives here.

## Data

Daily snow depth and snow water equivalent from USDA NRCS SNOTEL stations
(AWDB REST API at `wcc.sc.egov.usda.gov`). Snowfall is estimated as the sum of each
day's rise in snow depth, so totals run well below resort-reported figures.
A season is October 1 to May 31.

## Refresh the data

```bash
./scripts/refresh.sh
```

Needs `curl` and Python 3, and network access to `wcc.sc.egov.usda.gov`.

## View locally

`index.html` is written as a page fragment for publishing as a Claude artifact, so it has
no `<html>` wrapper of its own. To preview it, serve the folder and open it in a browser:

```bash
python3 -m http.server 8000
```
