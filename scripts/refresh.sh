#!/usr/bin/env bash
# Re-download SNOTEL daily readings and rebuild data.json (run from the project root).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data-raw
START=$(python3 -c "import datetime as d;t=d.date.today();y=t.year if t.month>=10 else t.year-1;print(f'{y-10}-09-30')")
END=$(date +%F)
curl -sS --fail -m 180 "https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1/data?stationTriplets=335:CO:SNTL,542:CO:SNTL,766:UT:SNTL,1168:NM:SNTL,689:WY:SNTL,590:MT:SNTL,874:CO:SNTL&elements=SNWD,WTEQ&duration=DAILY&beginDate=${START}&endDate=${END}" -o data-raw/daily.json
python3 scripts/build_data.py data-raw/daily.json data.json
