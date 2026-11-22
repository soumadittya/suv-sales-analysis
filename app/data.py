"""Loads app_data/ once and answers the questions the pages ask.

The notebook (suv_research.ipynb) writes every file in app_data/; the app only
reads them. Nothing here fits a model: at run time the app filters, sorts and
looks things up in about 1,400 rows.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

from . import fmt

APP_DATA = Path(__file__).resolve().parent.parent / "app_data"
KEY = ["company", "model", "variant"]

# app_data stores "None" as text for "no sunroof" and "no electric seats".
# pandas turns that word into a missing value by default, which would show a
# known "No" as "Not listed", so only truly empty cells count as missing.
READ_OPTIONS = dict(keep_default_na=False, na_values=[""], low_memory=False)

# Finder options that the Fuel and Seats selects already cover.
FUEL_OPTIONS = {"Diesel", "Electric", "CNG", "Strong hybrid"}
SEATS_OPTION = "7 or more seats"

# The options shown first; the rest fold away under "More options".
MAIN_OPTIONS = [
    "Automatic",
    "Any sunroof",
    "ADAS (automatic emergency braking)",
    "360° camera",
    "Ventilated seats",
    "6 or more airbags",
    "Cruise control",
    "Wireless phone charging",
    "5-star crash rating (Bharat or Global NCAP)",
]

FUELS = ["Petrol", "Diesel", "Electric", "CNG"]
SEATS = {"5": "5 or fewer", "6": "6", "7": "7 or more"}
PAGE_SIZE = 20
MAX_COMPARE = 4


def slugify(text: str) -> str:
    """'Tata Nexon EV Fearless 45' -> 'tata-nexon-ev-fearless-45'."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def read(folder: Path, name: str) -> pd.DataFrame:
    return pd.read_csv(folder / name, **READ_OPTIONS)


@dataclass(frozen=True)
class Option:
    """One Finder checkbox: `key` goes in the URL, `label` is the finder_flags column."""

    key: str
    label: str
    main: bool


class Store:
    """Every table the pages need, indexed by the variant's slug."""

    def __init__(self, folder: Path = APP_DATA):
        variants = read(folder, "variants_clean.csv")
        fair = read(folder, "fair_prices.csv")
        ladders = read(folder, "trim_ladders.csv")
        flags = read(folder, "finder_flags.csv")
        beaten = read(folder, "dominated_variants.csv")

        fair = fair[KEY + ["fair_price", "difference_pct", "badge", "missing_vs_price_peers", "better_value_alternatives"]]
        ladders = ladders[KEY + ["ladder", "position", "rungs", "price_jump", "features_added", "features_removed",
                                 "changes", "step_value", "sweet_spot", "also_good", "looks_only", "paint_only", "style_of"]]
        beaten = beaten[KEY + ["beaten_by_company", "beaten_by_model", "beaten_by_variant", "beaten_by_price", "saving"]]

        table = variants.merge(fair, on=KEY, how="left").merge(ladders, on=KEY, how="left").merge(beaten, on=KEY, how="left").copy()
        table["name"] = table["company"] + " " + table["model"] + " " + table["variant"]
        table["slug"] = table["name"].map(slugify)
        if table["slug"].duplicated().any():
            raise ValueError("Two variants share a URL slug; make slugify() more specific.")
        # The ladder file stores True/False with blanks for style versions.
        table["sweet_spot"] = table["sweet_spot"].astype(str).eq("True")
        table["also_good"] = table["also_good"].astype(str).eq("True")
        self.table = table.set_index("slug", drop=False)

        option_labels = [c for c in flags.columns if c not in KEY + ["ex_showroom_price"]]
        flags = flags.assign(slug=(flags["company"] + " " + flags["model"] + " " + flags["variant"]).map(slugify))
        self.flags = flags.set_index("slug")[option_labels].astype(str).eq("True").reindex(self.table.index)
        self.options = [
            Option(slugify(label), label, label in MAIN_OPTIONS)
            for label in option_labels
            if label not in FUEL_OPTIONS and label != SEATS_OPTION
        ]
        # Main options first, in the order the design lists them.
        self.options.sort(key=lambda o: (not o.main, MAIN_OPTIONS.index(o.label) if o.main else 0))
        self.option_by_key = {o.key: o for o in self.options}

        self.slug_by_name = dict(zip(self.table["name"], self.table["slug"]))
        self.spec_sheet = self._spec_sheet(read(folder, "spec_sheet.csv"))

        self.price_date = fmt.long_date(self.table["price_date"].iloc[0])
        self.city = self.table["on_road_city"].iloc[0]

    @staticmethod
    def _spec_sheet(rows: pd.DataFrame) -> dict[str, list[tuple[str, list[tuple[str, str]]]]]:
        """slug -> [(section, [(feature, details), ...]), ...] in CarDekho's order."""
        sheet: dict[str, dict[str, list[tuple[str, str]]]] = {}
        names = (rows["company"] + " " + rows["model"] + " " + rows["variant"]).map(slugify)
        for slug, category, feature, details in zip(names, rows["category"], rows["feature_name"], rows["feature_details"]):
            sections = sheet.setdefault(slug, {})
            sections.setdefault(category, []).append((feature, "" if fmt.is_missing(details) else details))
        return {slug: list(sections.items()) for slug, sections in sheet.items()}

    # ---- facts for the About page ----------------------------------------

    def counts(self) -> dict:
        t = self.table
        badges = t["badge"].value_counts()
        return {
            "variants": len(t),
            "models": t.groupby(["company", "model"]).ngroups,
            "brands": t["company"].nunique(),
            "badges": {b: int(badges.get(b, 0)) for b in ["Fair", "Overpriced", "Good value", "Not enough data"]},
            "price_date": self.price_date,
            "city": self.city,
        }

    # ---- Find page --------------------------------------------------------

    def find(self, max_lakh: float | None, fuel: str, seats: str, must: list[str], sort: str) -> pd.DataFrame:
        """Every variant within budget that has all the ticked options."""
        rows = self.table
        keep = pd.Series(True, index=rows.index)
        if max_lakh is not None:
            keep &= rows["ex_showroom_price"] <= max_lakh * 1e5
        if fuel in FUELS:
            keep &= rows["fuel_type"] == fuel
        if seats == "5":
            keep &= rows["seats"] <= 5
        elif seats == "6":
            keep &= rows["seats"] == 6
        elif seats == "7":
            keep &= rows["seats"] >= 7
        for key in must:
            option = self.option_by_key.get(key)
            if option is not None:
                keep &= self.flags[option.label]
        found = rows[keep]
        if sort == "value":
            # Furthest below the fair price first; unknown verdicts last.
            return found.sort_values(["difference_pct", "ex_showroom_price"], na_position="last")
        return found.sort_values(["ex_showroom_price", "name"])

    def search(self, query: str, limit: int = 50) -> pd.DataFrame:
        """Variants whose full name contains every word typed, cheapest first."""
        words = [w for w in re.split(r"\s+", query.lower().strip()) if w]
        if not words:
            return self.table.iloc[0:0]
        names = self.table["name"].str.lower()
        keep = pd.Series(True, index=self.table.index)
        for word in words:
            keep &= names.str.contains(word, regex=False)
        return self.table[keep].sort_values(["ex_showroom_price", "name"]).head(limit)

    # ---- Variant page -----------------------------------------------------

    def get(self, slug: str) -> pd.Series | None:
        return self.table.loc[slug] if slug in self.table.index else None

    def ladder(self, row: pd.Series) -> dict | None:
        """The trims of this variant's ladder (same model, fuel, gearbox and engine)."""
        if fmt.is_missing(row["ladder"]):
            return None
        rungs = self.table[self.table["ladder"] == row["ladder"]]
        trims = rungs[rungs["position"].notna()].sort_values("position")
        styles = rungs[rungs["position"].isna()].sort_values("ex_showroom_price")
        # A style version (same features, different looks) points at its trim.
        this_trim = row["variant"] if fmt.is_missing(row["style_of"]) else row["style_of"]
        sweet = trims[trims["sweet_spot"]]
        fuel, gearbox, power = row["ladder"].split(" | ")[1:4]
        return {
            "label": f"{row['model']}, {fuel.lower()} {gearbox.lower()}, {power}",
            "trims": trims,
            "styles": styles,
            "this_trim": this_trim,
            "sweet": sweet.iloc[0] if len(sweet) else None,
            "also_good": trims[trims["also_good"]],
        }

    def sweet_spot_sentence(self, row: pd.Series, ladder: dict) -> str:
        """One sentence pointing to the best-value trim, from the ladder's step values."""
        sweet = ladder["sweet"]
        trims = ladder["trims"]
        if sweet is None or len(trims) < 2:
            return ""
        here = trims[trims["variant"] == ladder["this_trim"]]
        if here.empty:
            return ""
        here_pos, sweet_pos = int(here["position"].iloc[0]), int(sweet["position"])
        here_price = row["ex_showroom_price"]  # the variant being viewed, which may be a style version
        if here_pos == sweet_pos:
            return "This is the best-value trim in its line-up."
        lo, hi = sorted([here_pos, sweet_pos])
        between = trims[(trims["position"] > lo) & (trims["position"] <= hi)]
        value = between["step_value"].fillna(0).sum()
        gap = abs(sweet["ex_showroom_price"] - here_price)
        if sweet_pos > here_pos:
            return (f"The best value here is the {sweet['variant']}. For {fmt.lakh(gap)} more than this one, "
                    f"it adds features worth about {fmt.lakh(value)}.")
        return (f"The best value here is the {sweet['variant']}. It costs {fmt.lakh(gap)} less, "
                f"and what this trim adds over it is worth about {fmt.lakh(value)}.")

    def alternatives(self, row: pd.Series) -> pd.DataFrame:
        """The notebook's better-value alternatives: similar variants closer to fair."""
        text = row["better_value_alternatives"]
        names = [] if fmt.is_missing(text) else [n.strip() for n in str(text).split(" | ")]
        slugs = [self.slug_by_name[n] for n in names if n in self.slug_by_name]
        return self.table.loc[slugs]

    def specs(self, slug: str):
        return self.spec_sheet.get(slug, [])

    # ---- Compare page -----------------------------------------------------

    def many(self, slugs: list[str]) -> pd.DataFrame:
        seen = []
        for s in slugs:
            if s in self.table.index and s not in seen:
                seen.append(s)
        return self.table.loc[seen[:MAX_COMPARE]]


@lru_cache(maxsize=1)
def get_store() -> Store:
    return Store()
