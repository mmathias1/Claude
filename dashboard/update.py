#!/usr/bin/env python3
"""Maintain the Discharge Docket news data and build the shareable page.

Data lives in dashboard/news.json. Subcommands:

  fr               Refresh the Federal Register list (EPA + Army Corps, last 365 days).
  add FILE         Merge news items from a JSON list in FILE (dedupes by URL).
  brief FILE       Replace today's brief with the JSON object in FILE.
  build            Stamp the update time and write dist/discharge-docket.html.
  validate         Check news.json against the expected shape.

Typical daily run:  fr -> add new.json -> brief brief.json -> build
"""
import datetime as dt
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "news.json"
TEMPLATE = HERE / "template.html"
DIST = HERE / "dist" / "discharge-docket.html"

CATEGORIES = {
    "wotus": "Navigable waters & §404",
    "npdes": "NPDES permits",
    "elg": "Effluent guidelines",
    "pfas": "PFAS",
    "municipal": "Sewage & stormwater",
    "certification": "§401 certification",
    "congress": "Congress",
    "courts": "Courts & enforcement",
    "states": "States & tribes",
    "industry": "Industry & energy",
}
NEWS_FIELDS = {"date", "title", "source", "url", "summary", "category"}
OPTIONAL_FIELDS = {"debate", "sections", "kind"}
MAX_NEWS = 400

FR_API = "https://www.federalregister.gov/api/v1/documents.json"
FR_TERMS = [
    '"effluent limitations"',
    "NPDES",
    '"pollutant discharge elimination system"',
    '"waters of the United States"',
    "pretreatment",
    '"water quality standards"',
    '"water quality certification"',
    "wastewater",
    "stormwater",
    "biosolids",
    '"sewage sludge"',
]
FR_AGENCIES = ["environmental-protection-agency", "engineers-corps"]
FR_FIELDS = [
    "title", "type", "abstract", "document_number", "html_url", "publication_date",
    "comments_close_on", "agencies", "citation", "docket_ids", "cfr_references",
]
WATER = re.compile(
    r"effluent|NPDES|pollutant discharge elimination|waters of the united states|"
    r"clean water act|wastewater|pretreatment|sewage|storm ?water|"
    r"water quality (standards|certification|criteria)|section 401|dredged|biosolids|"
    r"point source category|navigable",
    re.I,
)
STRONG = re.compile(r"effluent|NPDES|pollutant discharge elimination|waters of the united states|"
                    r"clean water act", re.I)
OFF_TOPIC_TITLE = re.compile(r"\bair\b|clean air act|emission|ozone|particulate|\bRCRA\b|"
                             r"approval and promulgation|advisory (board|committee)|public meeting", re.I)
SKIP_TITLE = re.compile(r"^agency information collection|^sunshine act|information collection request", re.I)


def today():
    return dt.date.today()


def load():
    if DATA.exists():
        return json.loads(DATA.read_text())
    return {"updated": None, "brief": None, "news": [], "federal_register": []}


def save(data):
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def norm_url(u):
    p = urllib.parse.urlsplit(u.strip())
    q = [(k, v) for k, v in urllib.parse.parse_qsl(p.query) if not k.lower().startswith("utm_")]
    return urllib.parse.urlunsplit((p.scheme.lower(), p.netloc.lower().removeprefix("www."),
                                    p.path.rstrip("/"), urllib.parse.urlencode(q), ""))


def check_item(it, where):
    missing = NEWS_FIELDS - it.keys()
    if missing:
        sys.exit(f"{where}: missing fields {sorted(missing)}")
    extra = it.keys() - NEWS_FIELDS - OPTIONAL_FIELDS
    if extra:
        sys.exit(f"{where}: unknown fields {sorted(extra)}")
    if it["category"] not in CATEGORIES:
        sys.exit(f"{where}: category must be one of {sorted(CATEGORIES)}")
    dt.date.fromisoformat(it["date"])
    if not it["url"].startswith("https://"):
        sys.exit(f"{where}: url must start with https://")


CLASS_RULES = [
    ("certification", r"section 401|water quality certification"),
    ("pfas", r"pfas|perfluoro|polyfluoro"),
    ("courts", r"consent decree|settlement agreement|enforcement"),
    ("municipal", r"sewage|sewer|biosolids|storm ?water|publicly owned treatment|financial capability"),
    ("elg", r"effluent limitations|point source category|pretreatment standards"),
    ("wotus", r"waters of the united states|navigable|nationwide permit|dredged|section 404"),
    ("states", r"\b(state|tribe|tribal)\b.*(program|standards|approval)|water quality standards"),
    ("npdes", r"npdes|pollutant discharge elimination|general permit"),
]


def classify(title, abstract=""):
    for text in (title, title + " " + abstract):
        for cat, pat in CLASS_RULES:
            if re.search(pat, text, re.I):
                return cat
    return "npdes"


def fetch_fr(days=365):
    since = (today() - dt.timedelta(days=days)).isoformat()
    docs = {}
    for term in FR_TERMS:
        params = [("conditions[term]", term), ("conditions[publication_date][gte]", since),
                  ("order", "newest"), ("per_page", "100")]
        params += [("conditions[agencies][]", a) for a in FR_AGENCIES]
        params += [("fields[]", f) for f in FR_FIELDS]
        url = FR_API + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=60) as r:
            res = json.load(r)
        for d in res.get("results", []):
            docs[d["document_number"]] = d
    out = []
    for d in docs.values():
        title, abstract = d.get("title") or "", d.get("abstract") or ""
        if SKIP_TITLE.search(title):
            continue
        if OFF_TOPIC_TITLE.search(title):
            continue
        if not (WATER.search(title) or STRONG.search(abstract)):
            continue
        out.append({
            "date": d["publication_date"],
            "title": title,
            "type": d.get("type"),
            "abstract": abstract[:600],
            "url": d["html_url"],
            "document_number": d["document_number"],
            "citation": d.get("citation"),
            "docket": (d.get("docket_ids") or [None])[0],
            "cfr": ", ".join(f'{c["title"]} CFR {c["part"]}' for c in (d.get("cfr_references") or [])
                             if c.get("part")) or None,
            "comments_close_on": d.get("comments_close_on"),
            "agencies": sorted({a.get("name") for a in d.get("agencies") or [] if a.get("name")}),
            "category": classify(title, abstract),
        })
    out.sort(key=lambda x: (x["date"], x["document_number"]), reverse=True)
    return out


def cmd_fr():
    data = load()
    data["federal_register"] = fetch_fr()
    save(data)
    print(f"federal_register: {len(data['federal_register'])} documents")


def cmd_add(path):
    data = load()
    new = json.loads(Path(path).read_text())
    if not isinstance(new, list):
        sys.exit("add: file must hold a JSON list of items")
    seen = {norm_url(n["url"]) for n in data["news"]}
    seen_titles = {n["title"].strip().lower() for n in data["news"]}
    added = 0
    for i, it in enumerate(new):
        check_item(it, f"item {i}")
        if norm_url(it["url"]) in seen or it["title"].strip().lower() in seen_titles:
            continue
        it.setdefault("sections", [])
        it.setdefault("kind", "news")
        it["added"] = today().isoformat()
        data["news"].append(it)
        seen.add(norm_url(it["url"]))
        seen_titles.add(it["title"].strip().lower())
        added += 1
    data["news"].sort(key=lambda x: x["date"], reverse=True)
    data["news"] = data["news"][:MAX_NEWS]
    save(data)
    print(f"added {added} of {len(new)} items; {len(data['news'])} total")


def cmd_brief(path):
    data = load()
    b = json.loads(Path(path).read_text())
    for k in ("summary", "aff", "neg"):
        if k not in b:
            sys.exit(f"brief: missing {k}")
    b["date"] = today().isoformat()
    data["brief"] = b
    save(data)
    print("brief updated")


def cmd_validate():
    data = load()
    for i, it in enumerate(data["news"]):
        check_item({k: v for k, v in it.items() if k != "added"}, f"news[{i}]")
    print(f"ok: {len(data['news'])} news, {len(data['federal_register'])} federal register")


def cmd_build():
    cmd_validate()
    data = load()
    data["updated"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    save(data)
    payload = {"categories": CATEGORIES, **data}
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.read_text().replace("/*__DATA__*/null", blob)
    DIST.parent.mkdir(exist_ok=True)
    DIST.write_text(page)
    print(f"built {DIST.relative_to(HERE.parent)} ({len(page) // 1024} KB)")


def main(argv):
    if not argv:
        sys.exit(__doc__)
    cmd, args = argv[0], argv[1:]
    {"fr": cmd_fr, "add": cmd_add, "brief": cmd_brief, "build": cmd_build,
     "validate": cmd_validate}.get(cmd, lambda *_: sys.exit(__doc__))(*args)


if __name__ == "__main__":
    main(sys.argv[1:])
