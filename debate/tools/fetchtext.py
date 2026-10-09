#!/usr/bin/env python3
"""Fetch a URL and print its readable text, exactly as it appears on the page.

Usage:
  fetchtext.py URL                     # print full page text
  fetchtext.py URL --grep WORD [-C N]  # print only lines containing WORD (case-insensitive), with N lines of context
  fetchtext.py URL --head N            # print first N lines
  fetchtext.py URL --find PHRASE [-W N] # search the FLATTENED text (all whitespace collapsed, exactly
                                       # what verify.py checks against); print N chars around each hit (default 700)
  fetchtext.py URL --flat              # print the whole flattened text

Raw responses are cached in ../cache (keyed by URL) so the verifier sees the same page.
Handles HTML and PDF.
"""
import hashlib, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(os.path.dirname(HERE), "cache")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def fetch_raw(url):
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha256(url.encode()).hexdigest()[:32]
    path = os.path.join(CACHE, key)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        r = subprocess.run(
            ["curl", "-sS", "-L", "--max-time", "60", "--compressed", "-A", UA,
             "-H", "Accept-Language: en-US,en;q=0.9",
             "-H", "Accept: text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
             "-o", path, "-w", "%{http_code}", url],
            capture_output=True, text=True)
        code = r.stdout.strip()
        if code != "200":
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
            sys.exit(f"FETCH FAILED: HTTP {code} {r.stderr.strip()} for {url}")
        with open(path + ".url", "w") as f:
            f.write(url)
    return path


def to_text(path):
    with open(path, "rb") as f:
        head = f.read(5)
    if head.startswith(b"%PDF"):
        r = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True)
        return r.stdout
    from bs4 import BeautifulSoup
    with open(path, "rb") as f:
        soup = BeautifulSoup(f.read(), "lxml")
    for t in soup(["script", "style", "noscript", "svg", "iframe", "template"]):
        t.decompose()
    text = soup.get_text("\n")
    lines = [re.sub(r"[ \t ]+", " ", ln).strip() for ln in text.splitlines()]
    out, blank = [], 0
    for ln in lines:
        if not ln:
            blank += 1
            if blank > 1:
                continue
        else:
            blank = 0
        out.append(ln)
    return "\n".join(out)


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    url = a[0]
    text = to_text(fetch_raw(url))
    if "--find" in a or "--flat" in a:
        from verify import norm
        flat = norm(text)
        if "--flat" in a:
            print(flat)
            return
        phrase = re.sub(r"\s+", "", norm(a[a.index("--find") + 1]).lower())
        w = int(a[a.index("-W") + 1]) if "-W" in a else 700
        # whitespace-insensitive search; map squashed index back to flat text
        idx = [k for k, ch in enumerate(flat) if not ch.isspace()]
        low = "".join(flat[k] for k in idx).lower()
        start, hits = 0, 0
        while hits < 15:
            j = low.find(phrase, start)
            if j < 0:
                break
            i = idx[j]
            print(f"[{i}] ...{flat[max(0, i - w // 3):i + w]}...\n--")
            start, hits = j + 1, hits + 1
        if not hits:
            print("NO MATCH")
        return
    if "--grep" in a:
        word = a[a.index("--grep") + 1].lower()
        c = int(a[a.index("-C") + 1]) if "-C" in a else 2
        lines = text.splitlines()
        shown = set()
        for i, ln in enumerate(lines):
            if word in ln.lower():
                for j in range(max(0, i - c), min(len(lines), i + c + 1)):
                    if j not in shown:
                        print(f"{j}: {lines[j]}")
                        shown.add(j)
                print("--")
    elif "--head" in a:
        n = int(a[a.index("--head") + 1])
        print("\n".join(text.splitlines()[:n]))
    else:
        print(text)


if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    main()
