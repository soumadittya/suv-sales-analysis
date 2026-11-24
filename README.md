# SUV Insights: Indian SUVs, ranked with reasons

A static website that sorts Indian SUVs into price segments and answers buyer questions about them:
- 26 questions for each price segment, such as the best value, the most feature loaded, the safest, where automatics or ADAS start, and the 7-seaters.
- The same 26 questions for each brand.
- 8 questions about the whole market.

Every answer comes with a reason.

It covers 1,399 SUV variants of 136 models from 25 brands, with New Delhi prices from CarDekho collected on 20 Nov 2026.

**Live site:** _link to be added after the first Render deploy_

## How it works

1. `scrapers/` collect every variant's features and prices from CarDekho into `data/`.
2. `notebooks/suv_research.ipynb` cleans the data and builds the fair-price model, which gives each variant the price its features usually cost. It writes the results to `app_data/`, and shows how each data problem was found and why each fix was chosen.
3. `notebooks/suv_insights.ipynb` defines the seven price segments (with each one's average price and standard deviation) and the scores (value for money, features, modern features, engine, safety). It then answers every question for each segment, each brand and the whole market, and writes the answers with their reasons to `insights_data/`.
4. `static_site/build.py` turns `insights_data/` into plain HTML pages in `site/`. Nothing is calculated while people browse, so the site needs no server code, database or JavaScript.

`app/` holds an earlier FastAPI version of the app (Find, Variant, Compare and About pages, reading `app_data/`), kept for now.

## Folders

```
static_site/               build.py, the page templates and the stylesheet
site/                      the built website (made by static_site/build.py; don't edit by hand)
insights_data/             suv_insights.ipynb's answers, which the site is built from (see its README)
app_data/                  suv_research.ipynb's output (see its README)
data/                      raw CarDekho data: one features file per variant, prices, scrape log
notebooks/                 suv_research.ipynb, then suv_insights.ipynb
scrapers/                  the two CarDekho scrapers (Python standard library only)
tests/                     pytest tests for the site and the earlier app
app/                       the earlier FastAPI app
sales-analysis-2020-2025/  an earlier study of the 20 best-selling SUVs, with its own README
requirements.txt           what the earlier FastAPI app needs to run
requirements-dev.txt       everything: the notebooks, the site build and the tests
.python-version            Python 3.13
```

## Build and view the site locally

With Python 3.13, from this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python static_site/build.py
```

Then open `site/index.html` in a browser, or serve the folder and open http://localhost:8010:

```bash
python -m http.server 8010 --directory site
```

Run the tests with `pytest -q`.

## Update the answers

1. Run `notebooks/suv_research.ipynb` (Restart & Run All). It rewrites `app_data/`.
2. Run `notebooks/suv_insights.ipynb`. It rewrites `insights_data/`.
3. Run `python static_site/build.py`. It rewrites `site/`.
4. Commit and push. The host serves the new pages.

To run a notebook from the command line instead, run this from the `notebooks/` folder:

```bash
jupyter execute --inplace suv_insights.ipynb
```

## Deploy on Render

`site/` is committed already built, so the host only has to serve files. Create a **Static Site** from this repository:

- **Branch:** `main`
- **Publish directory:** `site`
- **Build command:** any command that succeeds, for example `echo "site/ is prebuilt"`

Static sites are free on Render. Every push to `main` publishes the new `site/`.

## The earlier FastAPI app

Run it locally with `uvicorn app.main:app --reload` and open http://localhost:8000. To host it on Render instead, create a Web Service:
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## Data

All data comes from CarDekho's variant pages. The prices are one snapshot: ex-showroom and on-road prices for New Delhi on 20 Nov 2026.
