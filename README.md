# SUV Insights: Indian SUVs, ranked with reasons

A static website that sorts Indian SUVs into price segments and answers buyer questions about them:
- 26 questions for each price segment, such as the best value, the most feature loaded, the safest, where automatics or ADAS start, and the 7-seaters.
- The same 26 questions for each brand.
- 8 questions about the whole market.

Every answer comes with a reason.

It covers 1,399 SUV variants of 136 models from 25 brands, with New Delhi prices from CarDekho collected on 20 Nov 2026.

**Live site:** _link to be added once GitHub Pages is switched on_

## How it works

1. `scrapers/` collect every variant's features and prices from CarDekho into `data/`.
2. `notebooks/suv_research.ipynb` cleans the data and builds the fair-price model, which gives each variant the price its features usually cost. It writes the results to `app_data/`, and shows how each data problem was found and why each fix was chosen.
3. `notebooks/suv_insights.ipynb` defines the seven price segments (with each one's average price and standard deviation) and the scores (value for money, features, modern features, engine, safety). It then answers every question for each segment, each brand and the whole market, and writes the answers with their reasons to `insights_data/`.
4. `static_site/build.py` turns `insights_data/` into plain HTML pages in `docs/`, which GitHub Pages serves. Nothing is calculated while people browse, so the site needs no server code or database. Its only script, `assets/dropdowns.js`, opens the collapsed sections that an in-page link points into; the pages work without it.

## Folders

```
data/              raw CarDekho data from scraping: one features file per variant, prices, scrape log
scrapers/          the two CarDekho scrapers (Python standard library only)
notebooks/         suv_research.ipynb, then suv_insights.ipynb
app_data/          suv_research.ipynb's results; suv_insights.ipynb reads the clean variants and fair prices from it
insights_data/     suv_insights.ipynb's results: the answers the website is built from (see its README)
static_site/       build.py, the page templates, the stylesheet and the dropdown script
docs/              the built website, published by GitHub Pages (made by static_site/build.py; don't edit by hand)
requirements.txt   the Python packages for the notebooks and the website build
```

Earlier work is kept on the branches `full-project-archive` and `archive`, which both hold the whole project from before this clean-up: the first web app (FastAPI, with Find, Variant, Compare and About pages), its tests, and a 2020–2025 sales study of the 20 best-selling SUVs.

## Build and view the site locally

With Python 3.13, from this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python static_site/build.py
```

Then open `docs/index.html` in a browser, or serve the folder and open http://localhost:8010:

```bash
python -m http.server 8010 --directory docs
```

## Update the answers

1. Run `notebooks/suv_research.ipynb` (Restart & Run All). It rewrites `app_data/`.
2. Run `notebooks/suv_insights.ipynb`. It rewrites `insights_data/`.
3. Run `python static_site/build.py`. It rewrites `docs/`.
4. Commit and push to `main`. GitHub Pages publishes the new pages.

To run a notebook from the command line instead, run this from the `notebooks/` folder:

```bash
jupyter execute --inplace suv_insights.ipynb
```

## Publish on GitHub Pages

`docs/` is committed already built, so GitHub only has to serve the files. It also holds an empty `.nojekyll` file, which tells GitHub Pages to serve them as they are.

1. On GitHub, open the repository's **Settings → Pages**.
2. Under **Build and deployment**, set **Source** to **Deploy from a branch**.
3. Choose the branch **`main`** and the folder **`/docs`**, then **Save**.
4. After a minute or two the site is live at `https://soumadittya.github.io/suv-sales-analysis/`. Add that link under "Live site" above.

GitHub Pages is free for public repositories. Every push to `main` that changes `docs/` republishes the site.

## Data

All data comes from CarDekho's variant pages. The prices are one snapshot: ex-showroom and on-road prices for New Delhi on 20 Nov 2026.
