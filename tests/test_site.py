"""Tests for the static site that static_site/build.py makes from insights_data/.

Run from the project folder:  pytest -q
The site is built into a temporary folder, so site/ itself is never touched.
"""

import csv
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag

import pytest

from static_site import build as site_build

DATA = Path(__file__).resolve().parent.parent / "insights_data"


def rows(name):
    with open(DATA / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class Page(HTMLParser):
    """Collects the links, ids, question blocks and scripts of one HTML page."""

    def __init__(self, text):
        super().__init__()
        self.links, self.ids, self.questions, self.scripts = [], set(), [], 0
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag in ("a", "link") and "href" in attrs:
            self.links.append(attrs["href"])
        if tag == "article" and "question" in attrs.get("class", ""):
            self.questions.append(attrs["id"])
        if tag == "script":
            self.scripts += 1


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("build") / "site"
    pages = site_build.build(out)
    parsed = {p: Page(p.read_text(encoding="utf-8")) for p in pages}
    return out, parsed


def test_every_page_is_built(site):
    out, pages = site
    segments, brands = rows("segments.csv"), rows("brands.csv")
    # home, brand list, overall and method, plus one page per segment and per brand
    assert len(pages) == 4 + len(segments) + len(brands)
    for s in segments:
        assert (out / "segments" / f"{site_build.slugify(s['segment'])}.html").is_file()
    assert (out / "assets" / "style.css").is_file()


def test_links_and_anchors_resolve(site):
    out, pages = site
    for path, page in pages.items():
        for href in page.links:
            if href.startswith(("http://", "https://")):
                continue
            target, anchor = urldefrag(href)
            target_path = (path.parent / target).resolve() if target else path
            assert target_path.is_file(), f"{path.name}: broken link {href}"
            if anchor:
                target_page = pages.get(target_path) or Page(target_path.read_text(encoding="utf-8"))
                assert anchor in target_page.ids, f"{path.name}: missing anchor {href}"


def test_every_question_is_on_every_page(site):
    out, pages = site
    questions = rows("questions.csv")
    count = {tab: sum(q["tab"] == tab for q in questions) for tab in ("segment", "brand", "overall")}
    for path, page in pages.items():
        if path.parent.name == "segments":
            assert len(page.questions) == count["segment"], path.name
        elif path.parent.name == "brands" and path.name != "index.html":
            assert len(page.questions) == count["brand"], path.name
    assert len(pages[(out / "overall.html").resolve()].questions) == count["overall"]


def test_top_answers_match_the_data(site):
    out, _ = site
    for a in rows("answers_segments.csv"):
        if a["question_id"] == "S01" and a["rank"] == "1":
            html = (out / "segments" / f"{site_build.slugify(a['group'])}.html").read_text(encoding="utf-8")
            block = html.split('id="s01"', 1)[1].split("</article>", 1)[0]
            assert a["name"] in block and a["metric"] in block, a["group"]


def test_segment_average_and_spread(site):
    """Each segment's average price and standard deviation match its variants, and are
    shown at the top of its page and on its home-page card."""
    out, _ = site
    prices = {}
    for v in rows("variants.csv"):
        prices.setdefault(v["segment"], []).append(float(v["ex_showroom_price"]))
    home = (out / "index.html").read_text(encoding="utf-8")
    for s in rows("segments.csv"):
        p = prices[s["segment"]]
        mean = sum(p) / len(p)
        sd = (sum((x - mean) ** 2 for x in p) / len(p)) ** 0.5   # population SD: every variant is included
        assert abs(float(s["avg_price"]) - mean) <= 1 and abs(float(s["std_price"]) - sd) <= 1, s["segment"]

        slug = site_build.slugify(s["segment"])
        head = (out / "segments" / f"{slug}.html").read_text(encoding="utf-8").split('id="top"', 1)[1].split("</header>", 1)[0]
        card = home.split(f'href="segments/{slug}.html"', 1)[1].split("</a>", 1)[0]
        for text in (site_build.lakh(s["avg_price"]), site_build.lakh(s["std_price"])):
            assert text in head and text in card, (s["segment"], text)


def test_no_javascript(site):
    _, pages = site
    assert all(page.scripts == 0 for page in pages.values())


def test_value_colours_follow_the_badges():
    assert site_build.tone("29% below fair price", "Good value") == "good"
    assert site_build.tone("2% above fair price", "Fair") == "plain"
    assert site_build.tone("average 13% below fair price") == "plain"
    assert site_build.tone("average 19% below fair price") == "good"
    assert site_build.tone("average 27% above fair price") == "bad"
    assert site_build.tone("safety 95") == "plain"


def test_build_never_deletes_a_folder_it_did_not_make(tmp_path):
    (tmp_path / "notes.txt").write_text("keep me")
    with pytest.raises(SystemExit):
        site_build.build(tmp_path)
    assert (tmp_path / "notes.txt").read_text() == "keep me"
