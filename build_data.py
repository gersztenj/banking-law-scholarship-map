"""
Build the dashboard data blob from the banking-law-review-scrape outputs.

Reads the curated CSVs in ../banking_law_review_scrape/outputs/ and emits
`data.js` (a single `window.DASH = {...}` global) that index.html consumes.
Loaded via <script src="data.js">, so it works on file:// and any static host
with no server, no fetch, no CORS.

Regenerate after the corpus changes:  python build_data.py
"""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "banking_law_review_scrape", "outputs")


def fix_mojibake(s):
    """Reverse the common UTF-8-as-Latin-1 double-encoding (â€™ -> ')."""
    if not s or not isinstance(s, str):
        return s
    if "Ã" in s or "â€" in s or "â" in s:
        try:
            return s.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return s
    return s


def rows(name):
    path = os.path.join(OUT, name)
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(x, default=0):
    try:
        if x is None or x == "" or str(x).lower() == "nan":
            return default
        v = float(x)
        return int(v) if v.is_integer() else v
    except (ValueError, TypeError):
        return default


# --------------------------------------------------------------------------
# 1. Topic-by-year matrix  ->  per-topic yearly series + totals
# --------------------------------------------------------------------------
# Drop the partial current-year row: recent years undercount from publication
# lag, so the trailing point would read as a false cliff.
PARTIAL_YEAR = 2026
tby = [r for r in rows("topic_by_year_banking.csv") if int(r["year"]) != PARTIAL_YEAR]
years = [int(r["year"]) for r in tby]
topic_cols = [c for c in tby[0].keys() if c != "year"]
topic_series = {}
for t in topic_cols:
    topic_series[t] = [num(r[t]) for r in tby]
topic_totals = {t: sum(v) for t, v in topic_series.items()}
# rank topics by total, drop the UNCLASSIFIED bucket from the headline view
ranked_topics = sorted(
    (t for t in topic_cols if t != "UNCLASSIFIED"),
    key=lambda t: topic_totals[t],
    reverse=True,
)

# --------------------------------------------------------------------------
# 2. Year totals  (overall + fintech overlay)
# --------------------------------------------------------------------------
yoy = {int(r["year"]): num(r["banking_articles"]) for r in rows("trends_yoy.csv")
       if int(r["year"]) != PARTIAL_YEAR}
fin = {int(r["year"]): num(r["fintech_articles"]) for r in rows("trends_fintech_yoy.csv")
       if int(r["year"]) != PARTIAL_YEAR}

# --------------------------------------------------------------------------
# 3. Topic acceleration (rising / falling, 2010-14 vs 2020-25)
# --------------------------------------------------------------------------
accel = []
for r in rows("trends_topic_acceleration.csv"):
    if r["topic"] == "UNCLASSIFIED":
        continue
    accel.append({
        "topic": r["topic"],
        "early": num(r["2010-2014_count"]),
        "late": num(r["2020-2025_count"]),
        "ratio": num(r["ratio"]),
        "direction": r["change_direction"],
    })

# topic counts by 5-year period (for the small-multiples / period view)
periods = []
period_cols = None
for r in rows("trends_by_topic_period.csv"):
    if r["topic"] == "UNCLASSIFIED":
        continue
    if period_cols is None:
        period_cols = [c for c in r.keys() if c not in ("topic", "total")]
    periods.append({
        "topic": r["topic"],
        "total": num(r["total"]),
        "counts": [num(r[c]) for c in period_cols],
    })

# --------------------------------------------------------------------------
# 4. Scholar explorer  (top 100, each with its full list of relevant titles)
# --------------------------------------------------------------------------
TOP_SCHOLARS = 100
# full banking-relevant title list per scholar (newest first)
titles_by_scholar = {}
for r in rows("scholar_titles.csv"):
    titles_by_scholar.setdefault(r["display_name"], []).append(
        {"year": num(r["year"]), "title": fix_mojibake(r["title"])})

scholars = []
for r in rows("top_banking_scholars.csv")[:TOP_SCHOLARS]:
    topics = []
    for i in (1, 2, 3):
        t = r.get(f"top_topic_{i}")
        n = num(r.get(f"top_topic_{i}_n"))
        if t and t != "nan":
            topics.append({"topic": t, "n": n})
    venues = [r.get(f"top_venue_{i}") for i in (1, 2, 3)]
    venues = [fix_mojibake(v) for v in venues if v and v != "nan"]
    scholars.append({
        "rank": num(r["rank"]),
        "name": fix_mojibake(r["display_name"]),
        "n": num(r["n_banking_articles"]),
        "first": num(r["first_year"]),
        "last": num(r["last_year"]),
        "aff": fix_mojibake(r.get("affiliation_openalex", "")) if r.get("affiliation_openalex", "") not in ("", "nan") else "",
        "topics": topics,
        "venues": venues,
        "titles": titles_by_scholar.get(r["display_name"], []),
    })

# --------------------------------------------------------------------------
# 5. Policy-footprint scorecard (congressional presence + revolving door)
# --------------------------------------------------------------------------
influence = []
for r in rows("influence_scorecard.csv"):
    influence.append({
        "scholar": fix_mojibake(r["scholar"]),
        "articles": num(r["articles"]),
        "presence": num(r["presence"]),
        "rd": r.get("revolving_door", "") or "",
        "rd_detail": r.get("rd_detail", "") or "",
        "collision": (r.get("collision", "") or "").strip() != "",
    })

# --------------------------------------------------------------------------
# 6. Lead / lag (the reactive-literature thesis)
# --------------------------------------------------------------------------
leadlag = []
for r in rows("leadlag_events.csv"):
    leadlag.append({
        "date": r["date"],
        "event": r["event"],
        "type": r["type"],
        "topic": r["topic"],
        "pre": num(r["pre3"]),
        "post": num(r["post3"]),
        "direction": r["direction"],
    })

# --------------------------------------------------------------------------
# 7. Venues by period & school concentration
# --------------------------------------------------------------------------
venues_period = []
vp_cols = None
for r in rows("trends_top_venues_by_period.csv"):
    if vp_cols is None:
        vp_cols = [c for c in r.keys() if c not in ("venue", "total")]
    venues_period.append({
        "venue": fix_mojibake(r["venue"]),
        "total": num(r["total"]),
        "counts": [num(r[c]) for c in vp_cols],
    })

schools = []
for r in rows("trends_school_concentration.csv"):
    # strip the source-composition annotation, e.g. "Yale (eYLS + JREG)" -> "Yale",
    # so no repository jargon (eYLS/faculty/CBLR) shows in the school labels.
    schools.append({
        "school": r["school_proxy"].split(" (")[0].strip(),
        "n": num(r["total_banking_articles"]),
        "top_topic": r["top_topic"],
    })

# --------------------------------------------------------------------------
# 8. Co-authorship clusters
# --------------------------------------------------------------------------
clusters = []
for r in rows("coauthor_components.csv"):
    members = [m.strip() for m in r["members"].split(";") if m.strip()]
    clusters.append({
        "size": num(r["component_size"]),
        "root": r["root"],
        "members": members,
    })
clusters.sort(key=lambda c: c["size"], reverse=True)

# --------------------------------------------------------------------------
# Headline meta
# --------------------------------------------------------------------------
meta = {
    "total_articles": sum(yoy.values()),
    "year_min": min(years),
    "year_max": max(years),
    "n_scholars": len(rows("top_banking_scholars.csv")),  # full corpus total
    "n_scholars_shown": len(scholars),                    # explorer cap (top 100)
    "n_topics": len([t for t in topic_cols if t != "UNCLASSIFIED"]),
    "period_cols": period_cols,
    "venue_period_cols": vp_cols,
}

DASH = {
    "meta": meta,
    "years": years,
    "topicSeries": topic_series,
    "topicTotals": topic_totals,
    "rankedTopics": ranked_topics,
    "yoy": [{"year": y, "all": yoy.get(y, 0), "fintech": fin.get(y, 0)} for y in years],
    "accel": accel,
    "periods": periods,
    "scholars": scholars,
    "influence": influence,
    "leadlag": leadlag,
    "venuesPeriod": venues_period,
    "schools": schools,
    "clusters": clusters,
}

with open(os.path.join(HERE, "data.js"), "w", encoding="utf-8") as f:
    f.write("window.DASH = ")
    json.dump(DASH, f, ensure_ascii=False, indent=0)
    f.write(";\n")

print("Wrote data.js")
print(f"  {meta['total_articles']} articles, {meta['year_min']}-{meta['year_max']}")
print(f"  {meta['n_scholars']} scholars, {meta['n_topics']} topics")
print(f"  {len(leadlag)} lead/lag events, {len(clusters)} co-author clusters")
