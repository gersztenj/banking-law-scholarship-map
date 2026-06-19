# The Banking-Law Scholarship Map

An interactive, dependency-free dashboard visualizing the banking-law-review
corpus (`../banking_law_review_scrape/outputs/`). A companion to the OCC trust
charter / GENIUS Act / state-stablecoin working papers.

## What's here

- `index.html` — the dashboard. Pure HTML/CSS/vanilla-JS with hand-rolled SVG
  charts. **No external libraries, no CDN, no build step.** Opens locally and
  deploys to any static host unchanged.
- `data.js` — the data blob (`window.DASH = {...}`), generated from the CSVs.
- `build_data.py` — regenerates `data.js`.

## Sections

1. **Topics over time** — yearly counts by doctrinal topic (toggle lines).
2. **Rising & fading** — 2010–14 vs 2020–25 dumbbell chart.
3. **Scholar explorer** — searchable/sortable table of every scholar (click a row).
4. **Reactive thesis** — pre/post-event article volume for major policy events.
5. **Policy footprint** — Congressional-Record presence + the revolving door.
6. **Venues** — top homes by five-year period.
7. **Communities** — co-authorship clusters.

## Regenerate the data

After the corpus changes, rebuild the data blob:

```
python build_data.py
```

It reads the CSVs in `../banking_law_review_scrape/outputs/` and rewrites `data.js`.
The partial current year (2026) is dropped so trend lines don't show a false cliff.

## View locally

Because `index.html` loads `data.js` via `<script src>`, opening the file
directly works in most browsers. To be safe (and to mirror hosting), serve it:

```
python -m http.server 8123 --directory .
# then open http://localhost:8123
```

## Deploy (when ready)

It's a static site, so any of these work with zero config:

- **GitHub Pages** — push this folder to a repo, enable Pages on the branch.
- **Netlify / Cloudflare Pages** — drag-and-drop the folder, or connect the repo.

## Caveats baked into the page

The footer states the corpus limits honestly: paywalled/ToS-restricted sources
(HeinOnline, Westlaw, Lexis, some flagship reviews) were not scraped, so venues
like the *Yale Law Journal*, *Stanford Law Review*, and *Banking Law Journal* are
undercounted; congressional "presence" is a name-match that can collide with
namesakes (flagged); lead/lag measures topic volume, not causal influence.
