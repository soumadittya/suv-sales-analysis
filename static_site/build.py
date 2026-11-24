"""Build the static website in site/ from the CSV files in insights_data/.

Every answer on the site was worked out by notebooks/suv_insights.ipynb, so the
site is plain HTML and CSS: nothing is calculated while people browse, and any
static host (Render static sites, GitHub Pages, Netlify) can serve it. The one
script, assets/dropdowns.js, only opens the collapsed sections a link points into.

Run from the project folder:
    python static_site/build.py
Then open site/index.html in a browser, or serve the folder:
    python -m http.server 8010 --directory site
"""

from __future__ import annotations

import csv
import re
import shutil
import sys
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_DIR = ROOT / "insights_data"
OUT_DIR = ROOT / "site"
MARKER = ".built-by-static-site"   # build() only ever deletes a folder that has this file

TAB_LABEL = {"segment": "Segments", "brand": "Brands", "overall": "Overall"}


# ---- reading the CSV files ---------------------------------------------------

def read(name: str) -> list[dict]:
    with open(DATA_DIR / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def number(text: str):
    return None if text in ("", None) else float(text)


# ---- formatting ----------------------------------------------------------------

def lakh(rupees) -> str:
    """1534000 -> '₹15.34 lakh'; 12500000 -> '₹1.25 crore'."""
    if rupees in (None, ""):
        return ""
    value = float(rupees)
    if value >= 1e7:
        return f"₹{value / 1e7:.2f} crore"
    return f"₹{value / 1e5:.2f} lakh"


def price_range(low, high) -> str:
    return lakh(low) if float(low) == float(high) else f"{lakh(low)} to {lakh(high)}"


def gap_text(difference) -> str:
    """-0.123 -> '12% below fair price' (whole percent, cut toward zero, as in the notebook)."""
    if difference is None:
        return "No fair price"
    whole = int(abs(difference) * 100)
    if whole < 1:
        return "At fair price"
    return f"{whole}% {'below' if difference < 0 else 'above'} fair price"


VALUE_LINE = 15   # the fair-price model's badge line, in percent


def tone(metric: str, badge: str = "") -> str:
    """Colour a value-for-money metric the way the badges work: green beyond 15% below
    the fair price ("Good value"), red beyond 15% above ("Overpriced"), plain otherwise."""
    if "fair price" not in metric.lower():
        return "plain"
    if badge:
        return {"Good value": "good", "Overpriced": "bad"}.get(badge, "plain")
    found = re.search(r"(\d+)% (below|above)", metric)
    if not found or int(found.group(1)) < VALUE_LINE:
        return "plain"
    return "good" if found.group(2) == "below" else "bad"


def plural(count: int, word: str) -> str:
    return f"{count:,} {word}{'' if count == 1 else 's'}"


def slugify(text: str) -> str:
    """'₹10–15 lakh' -> '10-15-lakh', 'Mercedes-Benz' -> 'mercedes-benz'."""
    text = text.replace("–", "-").replace("—", "-")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def long_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%b %Y')}"


# ---- the data, arranged for the pages -----------------------------------------

class Site:
    """Everything the templates need, read once from insights_data/."""

    def __init__(self):
        self.variants = read("variants.csv")
        self.by_name = {v["name"]: v for v in self.variants}
        self.questions = defaultdict(list)
        for q in sorted(read("questions.csv"), key=lambda q: (q["tab"], int(q["order"]))):
            self.questions[q["tab"]].append(q)

        self.answers = defaultdict(list)
        for file_name in ["answers_segments.csv", "answers_brands.csv", "answers_overall.csv"]:
            for a in read(file_name):
                self.answers[(a["tab"], a["group"], a["question_id"])].append(a)

        self.segments = []
        for s in read("segments.csv"):
            s["slug"] = slugify(s["segment"])
            self.segments.append(s)
        self.segment_slug = {s["segment"]: s["slug"] for s in self.segments}

        self.brands = []
        for b in read("brands.csv"):
            b["slug"] = slugify(b["brand"])
            b["segment_list"] = [x.strip() for x in b["segments"].split(";") if x.strip()]
            self.brands.append(b)
        self.brand_slug = {b["brand"]: b["slug"] for b in self.brands}

        self.segment_models = read("segment_models.csv")
        self.model_stats = {m["model_name"]: m for m in read("models.csv")}
        self.feature_lists = read("feature_lists.csv")

        dates = {v["price_date"] for v in self.variants if v["price_date"]}
        self.price_date = long_date(max(dates)) if dates else ""
        self.totals = {
            "variants": len(self.variants),
            "models": len({v["model_name"] for v in self.variants}),
            "brands": len({v["company"] for v in self.variants}),
        }

    # one table row per variant, for the "cars in this group" lists
    def variant_row(self, v: dict) -> dict:
        difference = number(v["difference_pct"])
        value = gap_text(difference)
        return {
            "variant": v["variant"], "url": v["cardekho_url"], "price": lakh(v["ex_showroom_price"]),
            "fuel": v["fuel"], "gearbox": v["gearbox"], "seats": v["seats"], "value": value, "tone": tone(value, v["badge"]),
        }

    def stats(self, name: str, shown: int) -> dict:
        """A model's average price and standard deviation over all its variants (from models.csv)."""
        m = self.model_stats[name]
        assert int(m["variants"]) == shown, f"{name}: the page lists {shown} variants, models.csv has {m['variants']}"
        note = ""
        if int(m["variants"]) == 1:
            note = "One variant, so no spread"
        elif float(m["std_price"]) == 0:
            note = "All variants cost the same, so no spread"
        return {"avg": lakh(m["avg_price"]), "std": "" if note else lakh(m["std_price"]), "note": note}

    def model_list(self, variants: list[dict], with_stats: bool = False) -> list[dict]:
        """Models with their variants, cheapest model first. with_stats adds each model's
        average price and standard deviation, which only make sense when every variant is listed."""
        grouped = defaultdict(list)
        for v in variants:
            grouped[v["model_name"]].append(v)
        models = []
        for name, rows in grouped.items():
            rows.sort(key=lambda v: (float(v["ex_showroom_price"]), v["variant"]))
            prices = [float(v["ex_showroom_price"]) for v in rows]
            models.append({
                "name": name, "slug": slugify(name), "count": plural(len(rows), "variant"),
                "prices": price_range(min(prices), max(prices)), "from": min(prices),
                "stats": self.stats(name, len(rows)) if with_stats else None,
                "variants": [self.variant_row(v) for v in rows],
            })
        return sorted(models, key=lambda m: (m["from"], m["name"]))

    def item(self, a: dict, root: str, local_models: set[str]) -> dict:
        """One ranked answer, ready to show."""
        kind = a["item_type"]
        url, external, price, badge = "", False, "", ""
        if kind == "variant":
            variant = self.by_name[a["name"]]
            url, external, price, badge = variant["cardekho_url"], True, lakh(a["price"]), variant["badge"]
        elif kind == "model":
            price = f"from {lakh(a['price'])}" if a["price"] else ""
            if slugify(a["name"]) in local_models:
                url = f"#model-{slugify(a['name'])}"
        elif kind == "brand" and a["name"] in self.brand_slug:
            url = f"{root}brands/{self.brand_slug[a['name']]}.html"
        return {
            "rank": int(float(a["rank"])), "name": a["name"], "url": url, "external": external, "price": price,
            "metric": a["metric"], "tone": tone(a["metric"], badge), "highlight": a["highlight"], "reason": a["reason"],
        }

    def categories(self, tab: str, group: str, root: str, local_models: set[str]) -> list[dict]:
        """The tab's questions, grouped by category, with this group's answers."""
        out, by_name = [], {}
        for q in self.questions[tab]:
            if q["category"] not in by_name:
                by_name[q["category"]] = {"name": q["category"], "slug": slugify(q["category"]), "questions": []}
                out.append(by_name[q["category"]])
            rows = self.answers[(tab, group, q["question_id"])]
            assert rows, f"no answer for {tab} / {group} / {q['question_id']}"
            by_name[q["category"]]["questions"].append({
                "id": q["question_id"], "text": q["question"],
                "notes": [r["reason"] for r in rows if r["item_type"] == "note"],
                "ranked": [self.item(r, root, local_models) for r in sorted(rows, key=lambda r: float(r["rank"])) if r["item_type"] != "note"],
            })
        return out


# ---- writing the pages -----------------------------------------------------------

def environment() -> Environment:
    env = Environment(loader=FileSystemLoader(HERE / "templates"), autoescape=select_autoescape(["html"]),
                      undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)
    env.filters["lakh"] = lakh
    env.globals["plural"] = plural
    return env


def build(out_dir: Path = OUT_DIR) -> list[Path]:
    site, env = Site(), environment()
    if out_dir.exists():
        if not (out_dir / MARKER).exists() and any(out_dir.iterdir()):
            sys.exit(f"Refusing to replace {out_dir}: it wasn't made by this script.")
        shutil.rmtree(out_dir)
    (out_dir / "segments").mkdir(parents=True)
    (out_dir / "brands").mkdir()
    shutil.copytree(HERE / "assets", out_dir / "assets")
    common = {"price_date": site.price_date, "totals": site.totals}
    written = []

    def write(path: str, template: str, **context):
        root = "../" * path.count("/")
        html = env.get_template(template).render(root=root, **common, **context)
        target = out_dir / path
        target.write_text(html, encoding="utf-8")
        written.append(target)

    # Home: the segments (Tab 1)
    best_value = {s["segment"]: site.answers[("segment", s["segment"], "S01")] for s in site.segments}
    home_segments = []
    for s in site.segments:
        top = [a for a in best_value[s["segment"]] if a["item_type"] != "note"]
        home_segments.append({**s, "best": top[0] if top else None})
    write("index.html", "home.html", tab="segment", title="Indian SUVs by price segment",
          segments=home_segments, n_questions=len(site.questions["segment"]))

    # One page per segment
    for i, s in enumerate(site.segments):
        members = [v for v in site.variants if v["segment"] == s["segment"]]
        models = site.model_list(members)
        local = {m["slug"] for m in models}
        write(f"segments/{s['slug']}.html", "group.html", tab="segment", title=s["segment"],
              kind="segment", group=s, heading=s["segment"],
              facts=f"{plural(int(s['variants']), 'variant')} of {plural(int(s['models']), 'model')} from "
                    f"{plural(int(s['brands']), 'brand')}, {price_range(s['from_price'], s['to_price'])}",
              models=models, cars_heading="Cars in this segment",
              cars_note="Each model's variants in this price band. Its other variants are in the neighbouring segments.",
              categories=site.categories("segment", s["segment"], "../", local),
              prev=site.segments[i - 1] if i > 0 else None,
              next=site.segments[i + 1] if i + 1 < len(site.segments) else None)

    # Brands (Tab 2): the list, then one page per brand
    write("brands/index.html", "brands.html", tab="brand", title="Brands", brands=site.brands,
          segment_slug=site.segment_slug, n_questions=len(site.questions["brand"]))
    for i, b in enumerate(site.brands):
        members = [v for v in site.variants if v["company"] == b["brand"]]
        models = site.model_list(members, with_stats=True)
        local = {m["slug"] for m in models}
        write(f"brands/{b['slug']}.html", "group.html", tab="brand", title=b["brand"],
              kind="brand", group=b, heading=b["brand"],
              facts=f"{plural(int(b['variants']), 'variant')} of {plural(int(b['models']), 'model')}, "
                    f"{price_range(b['from_price'], b['to_price'])}",
              models=models, cars_heading=f"{b['brand']} models",
              cars_note="Every variant of each model, cheapest first, with the average price and standard deviation of the model's variants.",
              categories=site.categories("brand", b["brand"], "../", local),
              prev=site.brands[i - 1] if i > 0 else None,
              next=site.brands[i + 1] if i + 1 < len(site.brands) else None)

    # Overall (Tab 3)
    write("overall.html", "overall.html", tab="overall", title="Overall",
          categories=site.categories("overall", "All SUVs", "", set()))

    # How the answers are worked out
    lists = defaultdict(list)
    for f in site.feature_lists:
        lists[f["list"]].append(f)
    write("method.html", "method.html", tab="", title="How the answers are worked out",
          segments=site.segments, lists=lists)

    (out_dir / MARKER).write_text("This folder is rebuilt by static_site/build.py; do not edit it by hand.\n")
    return written


if __name__ == "__main__":
    pages = build()
    print(f"Built {len(pages)} pages in {OUT_DIR.relative_to(ROOT)}/")
