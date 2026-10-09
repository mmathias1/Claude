#!/usr/bin/env python3
"""Give each bookmark in a .docx a unique numeric id (docx-js writes id=1 for all)."""
import re, sys, zipfile, shutil, tempfile
src = sys.argv[1]
tmp = tempfile.mktemp(suffix=".docx")
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == "word/document.xml":
            xml = data.decode("utf-8")
            n = iter(range(1, 10**6))
            # each bookmarkStart is immediately followed (after its runs) by its bookmarkEnd, in order
            out, cur = [], None
            for part in re.split(r"(<w:bookmark(?:Start|End) [^>]*/>)", xml):
                if part.startswith("<w:bookmarkStart"):
                    cur = next(n)
                    part = re.sub(r'w:id="\d+"', f'w:id="{cur}"', part)
                elif part.startswith("<w:bookmarkEnd"):
                    part = re.sub(r'w:id="\d+"', f'w:id="{cur}"', part)
                out.append(part)
            data = "".join(out).encode("utf-8")
        zout.writestr(item, data)
shutil.move(tmp, src)
print("bookmark ids renumbered")
