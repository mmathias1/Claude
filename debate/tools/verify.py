#!/usr/bin/env python3
"""Check that every quote in the given JSON files appears verbatim on its URL's page.

Usage: verify.py out/group1.json [more.json ...]   (or a directory)
Each JSON file is a list of entries with at least "url" and "quote".
Matching ignores only whitespace/line-break differences and curly-vs-straight
quote/dash characters; every word and punctuation mark must match.
Prints PASS/FAIL per entry and writes <file>.verified.json with a "verified" flag.
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fetchtext import fetch_raw, to_text  # noqa: E402

TRANS = str.maketrans({
    "‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'",
    "“": '"', "”": '"', "„": '"', "″": '"',
    "–": "-", "—": "-", "‒": "-", "‐": "-", "‑": "-", "−": "-",
    " ": " ", " ": " ", " ": " ", "­": "",
})


def norm(s):
    s = s.translate(TRANS)
    s = re.sub(r"-\s*\n\s*", "-", s)  # pdf line-break hyphens kept as hyphen
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r" ([,.;:!?)\]])", r"\1", s)
    s = re.sub(r"([(\[]) ", r"\1", s)
    return s.strip()


def squash(s):
    return re.sub(r"\s+", "", s)


_page_cache = {}


def page(url):
    if url not in _page_cache:
        try:
            _page_cache[url] = norm(to_text(fetch_raw(url)))
        except SystemExit as e:
            _page_cache[url] = None
            print(f"   ! {e}")
    return _page_cache[url]


def main():
    files = []
    for a in sys.argv[1:]:
        if os.path.isdir(a):
            files += sorted(os.path.join(a, f) for f in os.listdir(a)
                            if f.endswith(".json") and not f.endswith(".verified.json"))
        else:
            files.append(a)
    tot = ok = 0
    for fn in files:
        entries = json.load(open(fn))
        for e in entries:
            tot += 1
            p = page(e["url"])
            q = norm(e["quote"])
            # whitespace-insensitive: only spacing/line breaks may differ; every character must match
            good = bool(p) and squash(q) in squash(p)
            e["verified"] = good
            ok += good
            print(f"{'PASS' if good else 'FAIL'} | {e.get('term','?')} | {e.get('source','?')} | {e['url']}")
            if not good and p:
                # show best partial match to help fix
                words = q.split()
                for n in (12, 8, 5):
                    if len(words) >= n and " ".join(words[:n]) in p:
                        i = p.index(" ".join(words[:n]))
                        print(f"   page has: {p[i:i+len(q)+40]!r}")
                        break
                print(f"   quote   : {q[:300]!r}")
        out = fn[:-5] + ".verified.json"
        json.dump(entries, open(out, "w"), indent=1, ensure_ascii=False)
    print(f"\n{ok}/{tot} verified")


if __name__ == "__main__":
    main()
