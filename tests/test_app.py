"""Tests for the SUV Value Guide app.

Run from the project folder:  pytest -q
They read the real files in app_data/, so they also check that the notebook's
outputs and the app still agree.
"""

import re

import pytest
from fastapi.testclient import TestClient

from app import fmt
from app.data import get_store
from app.main import app

client = TestClient(app)
NEXON = "/variant/tata-nexon-ev-fearless-45"


def text(html: str) -> str:
    """Page text without tags, on one line."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


# ---- formatting -------------------------------------------------------------

@pytest.mark.parametrize("value, expected", [
    (1534000, "₹15.34 lakh"), (1327500, "₹13.28 lakh"), (49000000, "₹490.00 lakh"),
])
def test_lakh(value, expected):
    assert fmt.lakh(value) == expected


@pytest.mark.parametrize("value, expected", [
    (1669184, "₹16,69,184"), (4600, "₹4,600"), (600, "₹600"), (49000000, "₹4,90,00,000"),
])
def test_rupees_use_indian_grouping(value, expected):
    assert fmt.rupees(value) == expected


@pytest.mark.parametrize("value, expected", [
    (0.183, "18% above"), (-0.1115, "11% below"), (0.1484, "14% above"),  # cut toward zero, never 15%
    (0.009, "at fair price"), (-0.0011, "at fair price"), (float("nan"), ""),
])
def test_difference_text(value, expected):
    assert fmt.difference_text(value) == expected


def test_short_list():
    assert fmt.short_list(["a"]) == "A"
    assert fmt.short_list(["a", "b"]) == "A and b"
    assert fmt.short_list(["a", "b", "c", "d"]) == "A, b, c and d"
    assert fmt.short_list(["a", "b", "c", "d", "e"]) == "A, b, c and 2 more"


# ---- data -------------------------------------------------------------------

def test_store_has_every_variant():
    counts = get_store().counts()
    assert counts["variants"] == 1399
    assert counts["models"] == 136
    assert sum(counts["badges"].values()) == 1399


def test_none_means_no_not_unknown():
    """'None' in app_data means 'doesn't have it'; pandas must not read it as missing."""
    row = get_store().get("tata-nexon-ev-fearless-45")
    assert row["sunroof"] == "None"
    assert fmt.sunroof(row["sunroof"]) == "No"


def test_finder_matches_the_mockup():
    store = get_store()
    found = store.find(15, "any", "any", ["automatic", "any-sunroof", "adas-automatic-emergency-braking"], "price")
    assert len(found) == 9
    assert found["ex_showroom_price"].is_monotonic_increasing
    assert found["name"].iloc[0] == "Mahindra XUV 3XO AX5 L Turbo AT"


def test_every_finder_option_filters():
    store = get_store()
    for option in store.options:
        found = store.find(None, "any", "any", [option.key], "price")
        assert 0 < len(found) < 1399, option.label


# ---- pages ------------------------------------------------------------------

def test_home_without_filters_lists_nothing():
    page = client.get("/")
    assert page.status_code == 200
    assert "variants match" not in page.text


def test_find_results_and_sort():
    url = "/?max=15&must=automatic&must=any-sunroof&must=adas-automatic-emergency-braking"
    page = text(client.get(url).text)
    assert "9 variants match" in page
    assert "From 4 models, up to ₹15 lakh, cheapest first." in page
    best = text(client.get(url + "&sort=value").text)
    assert "best value first" in best


def test_search():
    page = text(client.get("/?q=nexon+ev+fearless").text)
    assert "Tata Nexon EV Fearless 45" in page


def test_variant_page_numbers():
    page = text(client.get(NEXON).text)
    assert "Overpriced 18% above" in page
    assert "Similar SUVs with these features cost about ₹12.97 lakh. This one costs ₹2.37 lakh more." in page
    assert "fair zone, ₹11.02–14.91 lakh" in page
    assert "The best value here is the Empowered 45. For ₹1.00 lakh more than this one, it adds features worth about ₹2.79 lakh." in page
    assert "On-road price ₹16,69,184" in page
    assert "Kia Syros EV HTK" in page


def test_variant_without_fair_price():
    page = text(client.get("/variant/land-rover-discovery-3-0-diesel-dynamic-hse").text)
    assert "Not enough data" in page


def test_unknown_variant_is_404():
    page = client.get("/variant/not-a-car")
    assert page.status_code == 404
    assert "Page not found" in page.text


def test_compare_add_and_remove():
    one = client.get("/compare?v=tata-nexon-ev-fearless-45&add=kia+syros+ev+htk+plus+er", follow_redirects=False)
    assert one.status_code == 303
    assert one.headers["location"].endswith("v=tata-nexon-ev-fearless-45&v=kia-syros-ev-htk-plus-er")
    page = text(client.get(one.headers["location"]).text)
    assert "Tata Nexon EV Fearless 45" in page and "Kia Syros EV HTK Plus ER" in page
    many = text(client.get("/compare?v=tata-nexon-ev-fearless-45&add=creta").text)
    assert "Pick one" in many


def test_compare_caps_at_four():
    slugs = list(get_store().table.index[:5])
    page = text(client.get("/compare?" + "&".join(f"v={s}" for s in slugs)).text)
    assert page.count("Remove") == 4


def test_about_uses_live_counts():
    page = text(client.get("/about").text)
    assert "1,399 SUV variants of 136 models from 25 brands" in page
    assert "1,091 Fair, 191 Overpriced, 113 Good value, and 4" in page
