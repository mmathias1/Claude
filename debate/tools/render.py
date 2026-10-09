#!/usr/bin/env python3
"""Render verified definition entries (out/*.verified.json) into one Markdown file.

Usage: render.py OUT_DIR OUTPUT.md
Only entries with "verified": true are included.
"""
import json, os, re, sys
from collections import OrderedDict

RESOLUTION = ("Resolved: The United States Federal Government should reform its policy or policies "
              "for the regulation of non-agricultural wastewater discharge into navigable waters")

# (section heading, [terms in display order])
SECTIONS = [
    ("Resolved", ["resolved"]),
    ("The", ["the"]),
    ("United States Federal Government", ["united states federal government", "federal government",
                                          "united states", "federal", "government"]),
    ("Should", ["should"]),
    ("Reform", ["reform", "reform its policy"]),
    ("Its", ["its"]),
    ("Policy / Policies", ["policy", "policies", "policy or policies"]),
    ("Or", ["or"]),
    ("For", ["for"]),
    ("Regulation", ["regulation", "regulate", "for the regulation of", "regulation of"]),
    ("Of", ["of"]),
    ("Non-agricultural / Agricultural", ["non-agricultural", "agricultural", "agriculture",
                                        "non-agricultural wastewater", "agricultural wastewater",
                                        "agricultural stormwater discharges",
                                        "return flows from irrigated agriculture",
                                        "concentrated animal feeding operation", "nonpoint source"]),
    ("Wastewater", ["wastewater", "sewage", "stormwater"]),
    ("Discharge", ["discharge", "wastewater discharge", "non-agricultural wastewater discharge",
                   "discharge of a pollutant", "pollutant", "point source", "effluent"]),
    ("Into", ["into"]),
    ("Navigable Waters", ["navigable waters", "navigable", "waters", "waters of the united states",
                          "navigable waters of the united states", "discharge into navigable waters",
                          "territorial seas", "contiguous zone", "ocean"]),
]

ALIASES = {
    "nonagricultural": "non-agricultural",
    "non-agricultural / nonagricultural": "non-agricultural",
    "for the regulation of / regulation of": "for the regulation of",
    "policy reform": "reform its policy",
    "reform its policy / policy reform": "reform its policy",
    "discharge of pollutants": "discharge of a pollutant",
    "discharge of a pollutant / discharge of pollutants": "discharge of a pollutant",
    "u.s. federal government": "united states federal government",
    "usfg": "united states federal government",
    "storm water": "stormwater",
    "nonpoint source pollution": "nonpoint source",
    "non-point source": "nonpoint source",
    "concentrated animal feeding operations": "concentrated animal feeding operation",
    "cafo": "concentrated animal feeding operation",
    "nonagricultural wastewater": "non-agricultural wastewater",
}


def key(term):
    t = re.sub(r"\s+", " ", term.strip().lower().strip('"'))
    return ALIASES.get(t, t)


def anchor(s):
    return re.sub(r"[^a-z0-9 -]", "", s.lower()).strip().replace(" ", "-")


def card(e):
    tag = e.get("tag") or ""
    cite = [f"**{e['source']}**"]
    if e.get("author") and e["author"] != e["source"]:
        cite.append(e["author"])
    if e.get("title"):
        cite.append(f"“{e['title']}”")
    cite.append(e.get("date") or "n.d.")
    cite.append(f"<{e['url']}>")
    cite.append(f"Accessed {e.get('accessed', '2026-10-09')}")
    lines = [f"**{tag}**", "", ", ".join(cite) + f" — *{e.get('source_type', '')}*"]
    if e.get("context"):
        lines += ["", f"<sub>Context: {e['context']}</sub>"]
    q = e["quote"].strip()
    lines += [""] + ["> " + (ln if ln.strip() else "") for ln in q.splitlines()]
    return "\n".join(lines)


def main():
    out_dir, dest = sys.argv[1], sys.argv[2]
    entries = []
    for f in sorted(os.listdir(out_dir)):
        if f.endswith(".verified.json"):
            entries += [e for e in json.load(open(os.path.join(out_dir, f))) if e.get("verified")]
    # de-duplicate identical (url, quote)
    seen, uniq = set(), []
    for e in entries:
        k = (e["url"], re.sub(r"\s+", " ", e["quote"]).strip())
        if k not in seen:
            seen.add(k)
            uniq.append(e)
    by_term = OrderedDict()
    for e in uniq:
        by_term.setdefault(key(e["term"]), []).append(e)

    placed = set()
    body, toc = [], []
    for heading, terms in SECTIONS:
        parts = []
        for t in terms:
            if t in by_term:
                placed.add(t)
                items = by_term[t]
                parts.append(f"### “{t}” ({len(items)})\n\n" +
                             "\n\n---\n\n".join(card(e) for e in items))
                toc.append((heading, t, len(items)))
        if parts:
            body.append(f"## {heading}\n\n" + "\n\n".join(parts))
    extra = [t for t in by_term if t not in placed]
    if extra:
        parts = []
        for t in extra:
            items = by_term[t]
            parts.append(f"### “{t}” ({len(items)})\n\n" +
                         "\n\n---\n\n".join(card(e) for e in items))
            toc.append(("Other related terms", t, len(items)))
        body.append("## Other related terms\n\n" + "\n\n".join(parts))

    total = sum(n for _, _, n in toc)
    head = [
        "# 2026–27 CCA Resolution: Definitions File",
        "",
        f"> **{RESOLUTION}**",
        "",
        f"**{total} definitions** across **{len(toc)} terms and phrases**. Every quote below was copied "
        "from the live page and automatically checked word-for-word against that page's text on 2026-10-09 "
        "(only spacing and curly-vs-straight quote marks may differ from what you see on screen). "
        "Entries that failed the check were removed.",
        "",
        "Card format: **tag** → citation (source, author, title, date, link, access date, source type) → "
        "optional context note → the full unedited quote.",
        "",
        "## Contents",
        "",
    ]
    cur = None
    for heading, t, n in toc:
        if heading != cur:
            head.append(f"- **{heading}**")
            cur = heading
        head.append(f"  - [{t}](#{anchor(chr(0x201c) + t + chr(0x201d) + ' (' + str(n) + ')')}) — {n}")
    with open(dest, "w") as f:
        f.write("\n".join(head) + "\n\n" + "\n\n".join(body) + "\n")
    print(f"wrote {dest}: {total} entries, {len(toc)} terms; unplaced terms: {extra}")


if __name__ == "__main__":
    main()
