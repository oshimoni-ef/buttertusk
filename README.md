# ButterTusk

Every showtime near you, sorted by start time and laid out on a timeline.

The site is one static page. A daily job fetches showtimes, checks them, and rebuilds the
page with the data inlined, then deploys it to GitHub Pages. If a refresh fails, the job
stops before deploying, so the last good site stays up.

```
pipeline/
  build.py            fetch -> check -> write dist/index.html and dist/showtimes.json
  config.json         provider, area (centers + radius), days to fetch, default zip
  schema.py           the normalized data shape every provider returns
  providers/
    seed.py           one-time snapshot in seed/snapshot.json (free, never changes)
    internationalshowtimes.py   live data from internationalshowtimes.com (needs a key)
  zips.py             zip centers for the area, from the US Census gazetteer
  test_pipeline.py    offline tests
site/template.html    the page; build.py fills its /*@@DATA@@*/ slot
.github/workflows/refresh.yml   daily refresh + deploy
```

## Run locally

```
python pipeline/build.py --provider seed
python -m unittest discover pipeline
```

Open `dist/index.html` in a browser.

## Data sources

| Provider | Cost | Status |
|---|---|---|
| `seed` | Free | Works. A one-time copy of Oct 26 - Nov 1, 2026 for 23 theaters around Framingham, Boston and Worcester. It never updates. |
| `internationalshowtimes` | 7-day free trial, then paid per market | Written from the public API docs, not yet run against the live API. |

There is no free, licensed source of US showtimes. Scraping Fandango or theater sites on a
schedule breaks their terms, so this project doesn't do it. The seed snapshot was copied by
hand once, for a personal prototype.

To switch to live data:

1. Start the International Showtimes trial and copy the API key.
2. Run it once locally and fix any field names the adapter gets wrong:
   `ISHOWTIMES_API_KEY=... python pipeline/build.py --provider internationalshowtimes`
3. In the GitHub repo: Settings -> Secrets and variables -> Actions. Add the secret
   `ISHOWTIMES_API_KEY` and the variable `SHOWTIMES_PROVIDER` = `internationalshowtimes`.

Adding another provider means one module in `pipeline/providers/` with `fetch(config)` that
returns the shape in `schema.py`.

## Deploy

1. Create a GitHub repo and push this folder.
2. Settings -> Pages -> Source: **GitHub Actions**.
3. Actions -> "Refresh showtimes and deploy" -> Run workflow. After that it runs every day.
