#!/usr/bin/env python3
"""Turn raw SNOTEL daily readings (AWDB REST API) into the tracker's data.json.

Usage: build_data.py <daily.json from /data endpoint> <out data.json>
Snowfall is estimated as the sum of day-over-day gains in the snow-depth sensor,
after removing one-day sensor spikes and ignoring gains with no snow water on the ground.
Season = Oct 1 .. May 31 (Feb 29 folded into Feb 28 so every season has 243 days).
"""
import json, sys, datetime as dt

RESORTS = [
    # id, name, state, station triplet, station name, station elev ft, miles from resort
    ("winter-park", "Winter Park", "CO", "335:CO:SNTL", "Berthoud Summit", 11300),
    ("aspen-snowmass", "Aspen / Snowmass", "CO", "542:CO:SNTL", "Independence Pass", 10570),
    ("snowbird-alta", "Snowbird / Alta", "UT", "766:UT:SNTL", "Snowbird", 9170),
    ("taos", "Taos", "NM", "1168:NM:SNTL", "Taos Powderhorn", 11020),
    ("jackson-hole", "Jackson Hole", "WY", "689:WY:SNTL", "Phillips Bench", 8170),
    ("big-sky", "Big Sky", "MT", "590:MT:SNTL", "Lone Mountain", 8820),
    ("wolf-creek", "Wolf Creek", "CO", "874:CO:SNTL", "Wolf Creek Summit", 10930),
]
N_PAST = 10           # completed seasons kept behind the current one
N_DAYS = 243          # Oct 1 .. May 31

def season_days(start_year):
    d = dt.date(start_year, 10, 1); end = dt.date(start_year + 1, 5, 31)
    out = []
    while d <= end:
        out.append(d); d += dt.timedelta(days=1)
    return out

def clean_depth(dates, depth):
    """Fill short gaps by carrying forward and remove one-day spikes/dropouts."""
    vals = [depth.get(d) for d in dates]
    last = None
    for i, v in enumerate(vals):
        if v is None or v < 0: vals[i] = last
        else: last = v
    vals = [0 if v is None else v for v in vals]
    for i in range(1, len(vals) - 1):
        a, b, c = vals[i - 1], vals[i], vals[i + 1]
        # isolated spike or dropout: far from both neighbours, neighbours agree
        if abs(b - a) >= 6 and abs(b - c) >= 6 and (b - a) * (b - c) > 0 and abs(a - c) <= max(3, 0.5 * abs(b - a)):
            vals[i] = round((a + c) / 2)
    return vals

def build(raw, through=None):
    by = {s["stationTriplet"]: s for s in raw}
    latest = None
    resorts = []
    for rid, name, state, trip, sname, elev in RESORTS:
        el = {e["stationElement"]["elementCode"]: e["values"] for e in by[trip]["data"]}
        depth = {dt.date.fromisoformat(v["date"]): v.get("value") for v in el["SNWD"]}
        swe = {dt.date.fromisoformat(v["date"]): v.get("value") for v in el["WTEQ"]}
        last_obs = max(d for d, v in depth.items() if v is not None)
        latest = last_obs if latest is None else min(latest, last_obs)
        seasons = []
        cur = last_obs.year if last_obs.month >= 10 else last_obs.year - 1
        y = cur - N_PAST
        while y <= cur:
            days = [d for d in season_days(y) if d <= last_obs]
            # include Sep 30 as the baseline for the first day's gain
            dd = clean_depth([days[0] - dt.timedelta(days=1)] + days, depth)
            cum, dep, new, total = [], [], [], 0
            for i, d in enumerate(days):
                gain = dd[i + 1] - dd[i]
                w = swe.get(d) or 0
                wprev = swe.get(d - dt.timedelta(days=1)) or 0
                if gain < 0 or (w <= 0 and wprev <= 0): gain = 0
                gain = min(gain, 48)
                if d.month == 2 and d.day == 29:      # fold leap day into Feb 28
                    total += gain; cum[-1] = total; dep[-1] = dd[i + 1]; new[-1] += gain
                    continue
                total += gain
                cum.append(total); dep.append(dd[i + 1]); new.append(gain)
            seasons.append({"season": f"{y}-{str(y + 1)[2:]}", "start": y, "cum": cum, "depth": dep,
                            "complete": len(cum) == N_DAYS})
            y += 1
        resorts.append({"id": rid, "name": name, "state": state,
                        "station": {"name": sname, "id": trip, "elev": elev}, "seasons": seasons})
    return {"through": latest.isoformat(), "nDays": N_DAYS, "resorts": resorts}

if __name__ == "__main__":
    raw = json.load(open(sys.argv[1]))
    out = build(raw)
    json.dump(out, open(sys.argv[2], "w"), separators=(",", ":"))
    for r in out["resorts"]:
        print(f'{r["name"]:18s}', " ".join(f'{s["season"][2:]}:{s["cum"][-1]:>3}' for s in r["seasons"]),
              "| peak depth", " ".join(f'{max(s["depth"]):>3}' for s in r["seasons"]))
    print("through", out["through"])
