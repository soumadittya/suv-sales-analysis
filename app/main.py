"""SUV Value Guide: a small server-rendered FastAPI app.

Four pages, no JavaScript:
    /                 Find: search, or filter by budget and must-haves
    /variant/{slug}   one variant: fair price, trims, alternatives, on-road price, specs
    /compare?v=...    up to four variants side by side
    /about            where the numbers come from

Run it with:  env-suv-sales-analyis/bin/uvicorn app.main:app --reload
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import fmt
from .compare import compare_rows
from .data import FUELS, MAX_COMPARE, PAGE_SIZE, SEATS, get_store

HERE = Path(__file__).resolve().parent

app = FastAPI(title="SUV Value Guide", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")

templates = Jinja2Templates(directory=HERE / "templates")
for name in ["lakh", "lakh_amount", "rupees", "difference_text", "number", "whole", "yes_no",
             "meta_line", "crash_rating", "sunroof", "split_list", "short_list", "is_missing"]:
    templates.env.filters[name] = getattr(fmt, name)
templates.env.globals["badge_class"] = fmt.BADGE_CLASS
templates.env.globals["NOT_LISTED"] = fmt.NOT_LISTED

# The fair price model's accuracy, from the Step 7 summary in suv_research.ipynb
# (cross-validated by model, so each estimate is for a model it never saw).
MODEL_ACCURACY = {"typical_error": "8.2%", "within_10": "58%", "within_20": "89%", "badge_cutoff": "15%"}


def page(request: Request, template: str, status_code: int = 200, **context) -> HTMLResponse:
    store = get_store()
    context.setdefault("source", {"date": store.price_date, "city": store.city})
    return templates.TemplateResponse(request, template, context, status_code=status_code)


def records(frame, store) -> list[dict]:
    """DataFrame rows as dicts for the templates, plus a link to any variant that beats each one."""
    out = []
    for r in frame.to_dict("records"):
        if not fmt.is_missing(r.get("beaten_by_variant")):
            name = f"{r['beaten_by_company']} {r['beaten_by_model']} {r['beaten_by_variant']}"
            r["beaten_name"], r["beaten_slug"] = name, store.slug_by_name.get(name)
        out.append(r)
    return out


def parse_lakh(text: str | None) -> float | None:
    """The budget box: blank or nonsense means no limit."""
    try:
        value = float(text) if text not in (None, "") else None
    except ValueError:
        return None
    return value if value is None or value > 0 else None


@app.get("/", response_class=HTMLResponse)
def find(
    request: Request,
    q: str = "",
    budget: str | None = Query(default=None, alias="max"),
    fuel: str = "any",
    seats: str = "any",
    must: list[str] = Query(default=[]),
    sort: str = "price",
    limit: int = PAGE_SIZE,
):
    store = get_store()
    max_lakh = parse_lakh(budget)
    must = [m for m in must if m in store.option_by_key]
    searched = bool(q.strip())
    filtered = not searched and (max_lakh is not None or fuel in FUELS or seats in SEATS or bool(must))
    limit = min(max(limit, PAGE_SIZE), 2000)

    results = None
    if searched:
        results = store.search(q)
    elif filtered:
        results = store.find(max_lakh, fuel, seats, must, sort)

    # Links that keep the current filters and change one thing.
    params = [("max", budget or ""), ("fuel", fuel), ("seats", seats)] + [("must", m) for m in must]
    def link(**change) -> str:
        current = [(k, v) for k, v in params + [("sort", sort)] if k not in change and v not in ("", "any")]
        return "/?" + urlencode(current + [(k, v) for k, v in change.items()])

    return page(
        request, "find.html",
        q=q, budget=budget or "", fuel=fuel, seats=seats, must=must, sort=sort, limit=limit,
        fuels=FUELS, seat_choices=SEATS, options=store.options,
        searched=searched, filtered=filtered,
        results=None if results is None else records(results.head(limit), store),
        total=0 if results is None else len(results),
        models=0 if results is None else results.groupby(["company", "model"]).ngroups,
        max_lakh=max_lakh,
        sort_price_link=link(sort="price"), sort_value_link=link(sort="value"),
        more_link=link(limit=limit + PAGE_SIZE),
        variants_total=len(store.table),
        models_total=store.counts()["models"],
    )


@app.get("/variant/{slug}", response_class=HTMLResponse)
def variant(request: Request, slug: str):
    store = get_store()
    row = store.get(slug)
    if row is None:
        raise HTTPException(status_code=404)
    ladder = store.ladder(row)
    alternatives = store.alternatives(row)
    fair = row["fair_price"]
    bar = None
    if not fmt.is_missing(fair):
        # The bar runs from 70% to 130% of the fair price (see the FairBar component).
        dot = (row["ex_showroom_price"] / fair - 0.7) / 0.6 * 100
        bar = {
            "dot": round(min(max(dot, 0), 100), 1),
            "clamped": dot < 0 or dot > 100,
            "zone_low": fair * 0.85,
            "zone_high": fair * 1.15,
            "gap": row["ex_showroom_price"] - fair,
        }
    compare_link = "/compare?" + urlencode([("v", slug)] + [("v", s) for s in alternatives["slug"].tolist()][: MAX_COMPARE - 1])
    if ladder:
        ladder = {**ladder, "trims": records(ladder["trims"], store), "styles": records(ladder["styles"], store),
                  "also_good": records(ladder["also_good"], store)}
    return page(
        request, "variant.html",
        row=records(row.to_frame().T, store)[0], bar=bar, ladder=ladder,
        sweet_sentence=store.sweet_spot_sentence(row, store.ladder(row)) if ladder else "",
        alternatives=records(alternatives, store), specs=store.specs(slug),
        missing=fmt.split_list(row["missing_vs_price_peers"]),
        compare_link=compare_link, compare_one="/compare?" + urlencode([("v", slug)]),
        slug_by_name=store.slug_by_name,
    )


@app.get("/compare", response_class=HTMLResponse)
def compare(
    request: Request,
    v: list[str] = Query(default=[]),
    add: str = "",
    diff: int = 0,
):
    store = get_store()
    chosen = store.many(v)
    slugs = chosen["slug"].tolist()
    message, choices = "", None

    if add.strip():
        if len(slugs) >= MAX_COMPARE:
            message = f"You can compare up to {MAX_COMPARE} variants. Remove one first."
        else:
            found = store.search(add, limit=20)
            found = found[~found["slug"].isin(slugs)]
            if len(found) == 1:
                target = "/compare?" + urlencode([("v", s) for s in slugs + [found["slug"].iloc[0]]] + ([("diff", 1)] if diff else []))
                return RedirectResponse(target, status_code=303)
            if found.empty:
                message = f"No variant matches “{add}”. Try a model name, like Creta or Nexon EV."
            else:
                choices = [
                    (r["name"], "/compare?" + urlencode([("v", s) for s in slugs + [r["slug"]]] + ([("diff", 1)] if diff else [])), r["ex_showroom_price"])
                    for _, r in found.iterrows()
                ]

    def without(slug: str) -> str:
        rest = [s for s in slugs if s != slug]
        return "/compare?" + urlencode([("v", s) for s in rest] + ([("diff", 1)] if diff else []))

    keep = [("v", s) for s in slugs]
    return page(
        request, "compare.html",
        chosen=records(chosen, store), rows=compare_rows(chosen, only_differences=bool(diff)) if len(chosen) else [],
        remove_links={s: without(s) for s in slugs}, slugs=slugs, add=add, diff=diff,
        message=message, choices=choices, max_compare=MAX_COMPARE,
        diff_link="/compare?" + urlencode(keep + ([] if diff else [("diff", 1)])),
    )


@app.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return page(request, "about.html", counts=get_store().counts(), accuracy=MODEL_ACCURACY)


@app.exception_handler(StarletteHTTPException)
def not_found(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return page(request, "not_found.html", status_code=404)
    return HTMLResponse(str(exc.detail), status_code=exc.status_code)
