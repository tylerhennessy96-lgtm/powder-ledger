#!/usr/bin/env python3
"""Collect the season-to-date snowfall each resort reports on its own snow report.

Usage: fetch_reported.py <out reported.json>

Each mountain is read from the resort's own public snow-report page or the data
feed that page loads. A mountain that cannot be read keeps its previous entry
(with its old date), so one broken source never blanks the page or fails the run.
Winter Park and resorts that publish no season total are listed with total = null.
"""
import datetime as dt
import html
import json
import re
import sys
import urllib.request

UA = "Mozilla/5.0 (compatible; snow-report-reader/1.0)"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,text/html;q=0.9"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", errors="replace")


def num(v):
    """A snowfall figure in inches, or None if it is missing or implausible."""
    try:
        if isinstance(v, dict):
            v = v.get("inches", v.get("value"))
        f = float(str(v).strip().strip('"'))
    except (TypeError, ValueError):
        return None
    return round(f, 1) if 0 <= f <= 1500 else None


def day(s):
    """Pull a YYYY-MM-DD date out of the timestamp formats these feeds use."""
    s = str(s or "")
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return m.group(0)
    m = re.search(r"([A-Z][a-z]{2})[a-z]* (\d{1,2}), (\d{4})", s)
    if m:
        try:
            return dt.datetime.strptime(" ".join(m.groups()), "%b %d %Y").date().isoformat()
        except ValueError:
            return None
    return None


def snowbird():
    r = json.loads(get("https://api.snowbird.com/api/v1/dor/drupal/snow-reports?sort=date&direction=desc"))[0]
    return {"total": num((r.get("computed") or {}).get("total")), "base": num(r.get("base_depth")), "asOf": day(r.get("date"))}


def alta():
    t = get("https://www.alta.com/weather")
    m = re.search(r'"dated_at":"([^"]+)"[^{}]*?"base_depth":"([^"]*)"[^{}]*?"year_to_date":"([^"]*)"', t)
    return {"total": num(m.group(3)), "base": num(m.group(2)), "asOf": day(m.group(1))}


def taos():
    s = json.loads(get("https://www.skitaos.com/api/conditions?season=winter"))["snowData"]
    return {"total": num(s.get("seasonTotal")), "base": num(s.get("base")), "asOf": None}


def jackson(where):
    j = json.loads(get("https://jacksonhole-prod.zaneray.com/api/snow.json"))
    s = j["snow"][where]
    return {"total": num(s.get("seasonTotalSnow")), "base": num(s.get("totalSnowDepth")), "asOf": day(j.get("lastModified"))}


def bigsky():
    j = json.loads(get("https://www.bigskyresort.com/api/reportpal?resortName=bs&useReportPal=true"))
    loc = j["currentConditions"]["resortLocations"]["location"][0]
    return {"total": num(loc.get("snowSeasonTotal")), "base": num(loc.get("base")), "asOf": day(j.get("updated"))}


def aspen(mountain):
    j = json.loads(get("https://www.aspensnowmass.com/AspenSnowmass/SnowReport/Feed?mountain=" + mountain))
    season = next((v for k, v in j.items() if "season" in k.lower()), None)   # not published today
    return {"total": num(season), "base": num(j.get("snowBase")), "asOf": day(j.get("lastUpdated"))}


def wolfcreek():
    t = get("https://wolfcreekski.com/snow-report/")
    t = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", t)
    t = re.sub(r"(\|\s*)+", "|", html.unescape(re.sub(r"<[^>]+>", "|", t)))
    ytd = re.search(r"Snowfall YTD\|\s*([\d.]+)", t)
    base = re.search(r"Midway Snow Depth\|\s*([\d.]+)", t)
    upd = re.search(r"Updated:\s*\|\s*([A-Z][a-z]{2} \d{1,2}, \d{4})", t)
    return {"total": num(ytd.group(1)), "base": num(base.group(1)) if base else None, "asOf": day(upd.group(1)) if upd else None}


# resort id -> mountains shown for it: (name, link people can open, reader or None[, secondary plot])
SOURCES = {
    "winter-park": [("Winter Park", "https://www.winterparkresort.com/the-mountain/mountain-report", None)],
    "aspen-snowmass": [
        ("Aspen Mountain", "https://www.aspensnowmass.com/four-mountains/snow-report", lambda: aspen("AspenMountain")),
        ("Snowmass", "https://www.aspensnowmass.com/four-mountains/snow-report", lambda: aspen("Snowmass")),
    ],
    "snowbird-alta": [
        ("Snowbird", "https://www.snowbird.com/the-mountain/mountain-report/current-conditions-weather/", snowbird),
        ("Alta", "https://www.alta.com/weather", alta),
    ],
    "taos": [("Taos Ski Valley", "https://www.skitaos.com/weather", taos)],
    "jackson-hole": [
        ("Jackson Hole summit", "https://www.jacksonhole.com/mountain-report", lambda: jackson("tramSummit")),
        ("Jackson Hole mid-mountain", "https://www.jacksonhole.com/mountain-report", lambda: jackson("midMountain"), True),
    ],
    "big-sky": [("Big Sky", "https://www.bigskyresort.com/snow-report", bigsky)],
    "wolf-creek": [("Wolf Creek", "https://wolfcreekski.com/snow-report/", wolfcreek)],
}


def main(out_path):
    try:
        old = json.load(open(out_path))["resorts"]
    except (OSError, ValueError, KeyError):
        old = {}
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    resorts, failed = {}, []
    for rid, mountains in SOURCES.items():
        items = []
        for i, (name, url, reader, *rest) in enumerate(mountains):
            item = {"name": name, "url": url, "total": None, "base": None, "asOf": None, "auto": reader is not None,
                    "secondary": bool(rest and rest[0])}
            if reader:
                try:
                    got = reader()
                    item.update(got)
                    item["asOf"] = item["asOf"] or today
                except Exception as e:  # keep yesterday's figure rather than blank the page
                    failed.append(f"{name}: {type(e).__name__}: {e}")
                    prev = (old.get(rid) or [])
                    if i < len(prev) and prev[i].get("name") == name:
                        item.update({k: prev[i].get(k) for k in ("total", "base", "asOf")})
            items.append(item)
            print(f'{name:28s} total={item["total"]} base={item["base"]} asOf={item["asOf"]}')
        resorts[rid] = items
    json.dump({"fetched": today, "resorts": resorts}, open(out_path, "w"), indent=1)
    for f in failed:
        print("FAILED", f, file=sys.stderr)
    readers = sum(1 for m in SOURCES.values() for x in m if x[2])
    if len(failed) == readers:
        sys.exit("every source failed; reported.json holds the previous figures")


if __name__ == "__main__":
    main(sys.argv[1])
