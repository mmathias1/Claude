# 2026–27 CCA Debate Resolution: Definitions

> Resolved: The United States Federal Government should reform its policy or policies for the regulation of non-agricultural wastewater discharge into navigable waters

- **[2026-27-resolution-definitions.md](2026-27-resolution-definitions.md)**: 330 definitions across 50 terms and phrases. Each one is a full, unedited quote with a citation and a link.
- `data/`: the same entries as JSON (term, tag, source, author, title, date, url, source_type, context, quote). Use this to build a .docx later.
- `tools/`: `fetchtext.py` (page text), `verify.py` (checks each quote word for word against its live page), `render.py` (rebuilds the Markdown from `data/`).

Re-check every quote: `python3 tools/verify.py data/` (writes `*.verified.json` next to each file).
