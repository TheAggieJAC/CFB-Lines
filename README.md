# Claude's CFB Power Lines

Live site: https://theaggiejac.github.io/CFB-Lines/

College football power ratings and a neutral-field line maker for all 138 FBS teams. Ratings blend this season's sportsbook spreads, final scores and SP+, and are refreshed every Sunday.

- `index.html` — the site (all math runs in the browser)
- `model/` — data and scripts that rebuild it: `python3 build.py WEEK ranks_wWEEK.json && python3 render.py`
