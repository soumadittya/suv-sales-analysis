# SUV Value Guide

A small web app for Indian SUV buyers and car reviewers. It answers three questions:

- Which variants have the features I need, within my budget?
- Is this variant's price fair for what it offers?
- Which trim of a model gives the most for the money?

It covers 1,399 SUV variants of 136 models from 25 brands, with New Delhi prices from CarDekho collected on 20 Nov 2026.

**Live app:** _link to be added after the first Render deploy_

## How it works

1. `scrapers/` collect every variant's features and prices from CarDekho into `data/`.
2. `notebooks/suv_research.ipynb` cleans the data, builds the fair-price model and the trim ladders, and writes the results to `app_data/`. It shows how each data problem was found and why each fix was chosen.
3. `app/` is a FastAPI app that reads `app_data/` and serves four pages: Find, Variant, Compare and About.

## Folders

```
app/                       FastAPI app: routes, page templates, CSS
app_data/                  the notebook's output, which the app reads (see its README)
data/                      raw CarDekho data: one features file per variant, prices, scrape log
notebooks/                 suv_research.ipynb
scrapers/                  the two CarDekho scrapers (Python standard library only)
tests/                     pytest tests for the app
sales-analysis-2020-2025/  an earlier study of the 20 best-selling SUVs, with its own README
requirements.txt           what the app needs to run (Render installs this)
requirements-dev.txt       the app plus the tests and the notebook
.python-version            Python 3.13
```

## Run it locally

With Python 3.13, from this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Then open http://localhost:8000. Run the tests with `pytest -q`.

## Rebuild the app's data

Open `notebooks/suv_research.ipynb` and run every cell (Restart & Run All). It rewrites all the files in `app_data/`. Restart the app to load them.

## Deploy on Render

Create a Web Service from this repository on the `main` branch:

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Instance type:** Free

Render reads the Python version from `.python-version`, and every push to `main` redeploys the app. The free instance sleeps after 15 minutes without visitors, so the first page after a quiet spell can take about a minute to load.

## Data

All data comes from CarDekho's variant pages. The prices are one snapshot: ex-showroom and on-road prices for New Delhi on 20 Nov 2026.
