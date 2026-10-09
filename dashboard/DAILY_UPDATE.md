# Discharge Docket — daily update runbook

Live page: https://claude.ai/artifact/Qj7YkqxEHaJZGTcWgpmmo4
Code: branch `claude/sweet-edison-dxo22d` of mmathias1/claude.

**The live page is the source of truth for the data.** Scheduled runs can read
the repo but cannot push to it, so each run starts by pulling the current data
out of the published page, not from `news.json` in git.

Resolution: *The United States Federal Government should reform its policy or
policies for the regulation of non-agricultural wastewater discharge into
navigable waters.*

## Steps

1. `git fetch origin claude/sweet-edison-dxo22d && git checkout claude/sweet-edison-dxo22d && git pull origin claude/sweet-edison-dxo22d`
2. Read the live page with the Artifact tool (`action: "read"`, `url` = the live
   page above). The result names the file it saved the full HTML to. Run
   `python3 dashboard/update.py extract <that file>` to load the current data.
   If the read fails, stop and report it; do not publish from git's copy.
   Then `python3 dashboard/update.py fr` — refreshes Federal Register documents (EPA + Army Corps).
3. Find new stories. Run several WebSearch queries for the last ~3 days, e.g.
   Clean Water Act news, NPDES permit, effluent limitations guidelines, PFAS
   wastewater discharge, WOTUS / waters of the United States, Section 401
   certification / permitting reform bill, sewage overflow / combined sewer
   consent decree, industrial wastewater enforcement, produced water discharge,
   coal ash / steam electric wastewater, Clean Water Act court ruling.
   Skip stories already in `dashboard/news.json` (compare URLs and titles).
4. Keep only stories that bear on federal regulation of non-agricultural
   wastewater discharge into navigable waters. Agricultural runoff/CAFO stories
   only if they bear on the topic's limits (category `courts` or `congress` etc.,
   with a topicality note). Prefer primary sources and reputable outlets. Never
   invent a URL or date: confirm each with the search result or WebFetch.
5. Write the new items to a scratch JSON list. Each item:
   ```json
   {
     "date": "YYYY-MM-DD",            // publication date of the story
     "title": "Headline",
     "source": "Outlet",
     "url": "https://...",
     "summary": "1–2 factual sentences in your own words.",
     "category": "wotus|npdes|elg|pfas|municipal|certification|congress|courts|states|industry",
     "sections": ["§402"],            // CWA sections touched, may be []
     "debate": "One sentence on Aff/Neg/uniqueness/topicality use."
   }
   ```
   Then `python3 dashboard/update.py add <file>`.
6. Write today's brief (`{"summary": "...", "aff": ["..."], "neg": ["..."]}`,
   2–3 sentences plus 2–3 bullets per side, built from the newest stories and
   any comment deadlines within 14 days) and run `python3 dashboard/update.py brief <file>`.
   If nothing new turned up, still refresh the brief so the date is current.
7. `python3 dashboard/update.py build` (validates, stamps the time, writes
   `dashboard/dist/discharge-docket.html`).
8. Publish with the Artifact tool: `file_path` = `dashboard/dist/discharge-docket.html`,
   `url` = the live page above. The page is fully regenerated from `news.json`,
   so the new build replaces the old one.
9. Do not commit or push; the scheduled session has no push access. Finish
   with a short summary of the stories added.
