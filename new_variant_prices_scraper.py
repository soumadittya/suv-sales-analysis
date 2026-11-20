"""Build new_variant_prices.csv: one row per variant in new_variant_links.csv with the
price table from its CarDekho variant page (the same page the features come from).

Columns:
    company, model, variant, ex_showroom_price, registration_charges, insurance, others,
    optional_accessories, on_road_price, on_road_city, emi_per_month, price_date
All prices are whole rupees. On-road prices are New Delhi only: when CarDekho has no
New Delhi price for a variant (it shows another city instead), only ex_showroom_price is
kept and the city-specific columns are left blank. A blank "others" or
"optional_accessories" means the page lists no such charge.

Pages are read from --cache (gzipped HTML saved by new_variant_features_scraper.py
--cache) when available, so prices match the features snapshot; anything missing is
downloaded. price_date is the date the page was downloaded.

Usage:
    python3 new_variant_prices_scraper.py --cache <html cache folder>
"""
import argparse
import csv
import datetime
import gzip
import os
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser

from new_variant_features_scraper import fetch, redirect_is_rename, same_page

CITY = 'New Delhi'
PRICE_COLUMNS = ['company', 'model', 'variant', 'ex_showroom_price', 'registration_charges',
                 'insurance', 'others', 'optional_accessories', 'on_road_price', 'on_road_city',
                 'emi_per_month', 'price_date']
LABEL_TO_COLUMN = {
    'Ex-Showroom Price': 'ex_showroom_price',
    'Registration Charges': 'registration_charges',
    'Insurance': 'insurance',
    'Others': 'others',
    'Optional': 'optional_accessories',
}
ON_ROAD_PREFIX = 'On-Road Price in '


def to_rupees(text):
    """'Rs.21,29,000' -> 2129000, '1.2 Cr' -> 12000000; None if there is no number."""
    m = re.search(r'(\d[\d,]*(?:\.\d+)?)\s*(Lakh|Cr|Crore)?', text.replace('Rs.', ''))
    if not m:
        return None
    n = float(m.group(1).replace(',', ''))
    unit = (m.group(2) or '').lower()
    n *= 1e5 if unit == 'lakh' else 1e7 if unit in ('cr', 'crore') else 1
    return int(round(n))


class PriceParser(HTMLParser):
    """Reads <section id="OnRoadPrice">: rows of (label, value) plus the EMI line.
    Label cells also hold tooltip text (<span class="othersinfo">) and, for "Optional",
    a checkbox <label>; both are skipped so only the row's own label is kept."""

    def __init__(self):
        super().__init__()
        self.depth = 0
        self.td_index = -1
        self.span_depth = 0
        self.skip_depth = 0
        self.label_done = False
        self.label, self.value = [], []
        self.rows = []
        self.in_emi = False
        self.emi = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'section' and a.get('id') == 'OnRoadPrice':
            self.depth = 1
            return
        if not self.depth:
            return
        cls = (a.get('class') or '').split()
        if tag == 'section':
            self.depth += 1
        elif tag == 'tr':
            self.td_index, self.label, self.value = -1, [], []
            self.span_depth, self.skip_depth, self.label_done = 0, 0, False
        elif tag == 'td':
            self.td_index += 1
        elif tag == 'span' and self.td_index == 0:
            self.span_depth += 1
            if self.skip_depth or 'othersinfo' in cls:
                self.skip_depth += 1
        elif tag == 'label' and self.td_index == 0:
            self.skip_depth += 1
        elif tag == 'div' and 'getfinance' in cls:
            self.in_emi = True

    def handle_endtag(self, tag):
        if not self.depth:
            return
        if tag == 'section':
            self.depth -= 1
        elif tag == 'span' and self.td_index == 0:
            if self.skip_depth:
                self.skip_depth -= 1
            self.span_depth -= 1
            if self.span_depth == 0 and ''.join(self.label).strip():
                self.label_done = True
        elif tag == 'label' and self.td_index == 0 and self.skip_depth:
            self.skip_depth -= 1
        elif tag == 'tr' and self.td_index >= 1:
            label = ' '.join(''.join(self.label).split())
            value = ' '.join(''.join(self.value).split())
            if label:
                self.rows.append((label, value, to_rupees(value)))
            self.td_index = -1
        elif tag == 'div' and self.in_emi:
            self.in_emi = False

    def handle_data(self, data):
        if not self.depth:
            return
        if self.in_emi:
            self.emi.append(data)
        elif self.td_index == 0 and not self.skip_depth and not self.label_done:
            self.label.append(data)
        elif self.td_index == 1:
            self.value.append(data)


def parse_price(html):
    p = PriceParser()
    p.feed(html)
    p.close()
    return p.rows, ' '.join(''.join(p.emi).split())


def price_row(link, html, price_date):
    """Return (csv_row, problem). problem is '' when the row is complete."""
    out = {c: '' for c in PRICE_COLUMNS}
    out.update(company=link['company'], model=link['model'], variant=link['variant'],
               on_road_city=CITY, price_date=price_date)
    rows, emi = parse_price(html)
    parts, city, on_road, unknown = {}, None, None, []
    for label, text, rupees in rows:
        if label.startswith(ON_ROAD_PREFIX):
            city, on_road = label[len(ON_ROAD_PREFIX):], rupees
        elif label in LABEL_TO_COLUMN and rupees is not None:
            parts[LABEL_TO_COLUMN[label]] = rupees
        else:
            unknown.append(f'{label}={text}')
    if 'ex_showroom_price' not in parts:
        return out, 'no price table on page'
    out['ex_showroom_price'] = parts['ex_showroom_price']
    if city != CITY:
        return out, f'no {CITY} on-road price (CarDekho shows {city}); city-specific columns left blank'
    out.update(parts)
    out['on_road_price'] = on_road
    out['emi_per_month'] = to_rupees(emi) or ''
    problems = []
    if unknown:
        problems.append('unrecognised rows: ' + '; '.join(unknown))
    if on_road != sum(parts.values()):
        problems.append(f'on-road {on_road} != sum of parts {sum(parts.values())}')
    return out, ' | '.join(problems)


def load_page(link, cache_dir, delay, listed_urls):
    """Return (html, price_date). Uses the cache when present, otherwise downloads."""
    cached = os.path.join(cache_dir, link['file_name'][:-4] + '.html.gz') if cache_dir else ''
    if cached and os.path.exists(cached):
        with gzip.open(cached, 'rt', encoding='utf-8') as f:
            html = f.read()
        return html, datetime.date.fromtimestamp(os.path.getmtime(cached)).isoformat()
    time.sleep(delay + random.uniform(0, delay))
    html, final_url = fetch(link['url'])
    if not same_page(final_url, link['url']) and not redirect_is_rename(link['url'], final_url, listed_urls):
        raise RuntimeError(f'redirected to {final_url}')
    if cached:
        with gzip.open(cached, 'wt', encoding='utf-8') as f:
            f.write(html)
    return html, datetime.date.today().isoformat()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--links', default='new_variant_links.csv')
    ap.add_argument('--out', default='new_variant_prices.csv')
    ap.add_argument('--cache', default='', help='folder of gzipped variant pages (read, and filled for misses)')
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--delay', type=float, default=1.0, help='base seconds to wait before each download')
    args = ap.parse_args()

    with open(args.links, newline='', encoding='utf-8') as f:
        links = list(csv.DictReader(f))
    if args.cache:
        os.makedirs(args.cache, exist_ok=True)
    listed_urls = frozenset(l['url'].lower() for l in links)

    def work(link):
        try:
            html, price_date = load_page(link, args.cache, args.delay, listed_urls)
        except Exception as e:
            out = {c: '' for c in PRICE_COLUMNS}
            out.update(company=link['company'], model=link['model'], variant=link['variant'], on_road_city=CITY)
            return out, f'page not loaded: {e}'
        return price_row(link, html, price_date)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(work, links))

    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=PRICE_COLUMNS)
        w.writeheader()
        w.writerows(row for row, _ in results)

    problems = [(link['file_name'], p) for link, (_, p) in zip(links, results) if p]
    complete = sum(1 for row, p in results if not p)
    print(f'{len(results)} rows written to {args.out}: {complete} complete, {len(problems)} with notes')
    for name, p in problems:
        print(f'  {name}: {p}')
    return 0 if all(row['ex_showroom_price'] != '' for row, _ in results) else 1


if __name__ == '__main__':
    sys.exit(main())
