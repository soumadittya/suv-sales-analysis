"""Scrape the specs & features table of every CarDekho variant page listed in
data/new_variant_links.csv and save one CSV per variant in data/new-variant-features/.

Each output file is named <company>-<model>-<variant>.csv (hyphens/spaces inside a
name become "_") and has the columns:
    company, model, variant, category, feature_name, feature_details
Tick / cross icons on CarDekho are stored as YES / NO.

Only the Python standard library is used. Re-running skips variants whose CSV
already exists (use --force to re-scrape), so an interrupted run can be resumed.
File paths default to the data/ folder next to scrapers/, so it runs from any folder.

Usage (from the project folder):
    python3 scrapers/new_variant_features_scraper.py             # scrape everything
    python3 scrapers/new_variant_features_scraper.py --limit 5   # quick test
"""
import argparse
import csv
import gzip
import os
import random
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser

# Default file locations: the data/ folder next to the scrapers/ folder.
DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data'))

USER_AGENT = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/130.0 Safari/537.36')
OUTPUT_COLUMNS = ['company', 'model', 'variant', 'category', 'feature_name', 'feature_details']
LOG_COLUMNS = ['company', 'model', 'variant', 'url', 'file_name', 'status', 'rows',
               'page_heading', 'final_url', 'error']


class SpecsParser(HTMLParser):
    """Collects (section, feature_name, feature_details) rows from <div id="scrollDiv">."""

    def __init__(self):
        super().__init__()
        self.in_scroll = False
        self.div_depth = 0
        self.in_h2 = False
        self.h2_text = []
        self.heading = ''
        self.in_h3 = False
        self.h3_text = []
        self.section = None
        self.in_tbody = False
        self.in_td = False
        self.hidden_depth = 0       # inside <span class="hide"> (screen-reader "Yes"/"No")
        self.cells = []             # [[text parts], icon value] per <td>
        self.rows = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'h2' and not self.heading:
            self.in_h2, self.h2_text = True, []
        if tag == 'div':
            if a.get('id') == 'scrollDiv':
                self.in_scroll, self.div_depth = True, 1
                return
            if self.in_scroll:
                self.div_depth += 1
        if not self.in_scroll:
            return
        if tag == 'h3':
            self.in_h3, self.h3_text = True, []
        elif tag == 'tbody':
            self.in_tbody = True
        elif tag == 'tr' and self.in_tbody:
            self.cells = []
        elif tag == 'td' and self.in_tbody:
            self.in_td = True
            self.cells.append([[], None])
        elif tag == 'i' and self.in_td:
            cls = a.get('class') or ''
            if 'icon-check' in cls:
                self.cells[-1][1] = 'YES'
            elif 'icon-deletearrow' in cls:
                self.cells[-1][1] = 'NO'
        elif tag == 'span' and self.in_td:
            if self.hidden_depth or 'hide' in (a.get('class') or '').split():
                self.hidden_depth += 1

    def handle_endtag(self, tag):
        if tag == 'h2' and self.in_h2:
            self.in_h2 = False
            text = ' '.join(''.join(self.h2_text).split())
            if 'specifications' in text.lower():
                self.heading = text
        if not self.in_scroll:
            return
        if tag == 'div':
            self.div_depth -= 1
            if self.div_depth == 0:
                self.in_scroll = False
        elif tag == 'h3':
            self.in_h3 = False
            self.section = ' '.join(''.join(self.h3_text).split())
        elif tag == 'tbody':
            self.in_tbody = False
        elif tag == 'td':
            self.in_td = False
        elif tag == 'span' and self.hidden_depth:
            self.hidden_depth -= 1
        elif tag == 'tr' and self.in_tbody and len(self.cells) == 2:
            name = ' '.join(''.join(self.cells[0][0]).split())
            text = ' '.join(''.join(self.cells[1][0]).split())
            value = text if text else (self.cells[1][1] or '')
            if name:
                self.rows.append((self.section, name, value))

    def handle_data(self, data):
        if self.in_h2:
            self.h2_text.append(data)
        elif self.in_h3:
            self.h3_text.append(data)
        elif self.in_td and not self.hidden_depth:
            self.cells[-1][0].append(data)


def parse_specs(html):
    p = SpecsParser()
    p.feed(html)
    p.close()
    return p.heading, p.rows


def make_ssl_context():
    """Verified TLS context. python.org builds on macOS ship without a CA store, so also
    load certifi's bundle (if installed) and the system bundle at /etc/ssl/cert.pem."""
    ctx = ssl.create_default_context()
    try:
        import certifi
        ctx.load_verify_locations(certifi.where())
    except ImportError:
        pass
    if os.path.exists('/etc/ssl/cert.pem'):
        ctx.load_verify_locations('/etc/ssl/cert.pem')
    return ctx


SSL_CONTEXT = make_ssl_context()


def fetch(url, retries=3, timeout=40):
    """Return (html, final_url). Retries on network errors, 429 and 5xx."""
    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'en-IN,en;q=0.9',
                'Accept-Encoding': 'gzip',
            })
            with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as resp:
                body = resp.read()
                if resp.headers.get('Content-Encoding') == 'gzip':
                    body = gzip.decompress(body)
                return body.decode('utf-8', errors='replace'), resp.geturl()
        except urllib.error.HTTPError as e:
            last_err = f'HTTP {e.code}'
            if e.code not in (429, 500, 502, 503, 504):
                break
        except Exception as e:  # timeouts, connection resets, SSL hiccups
            last_err = f'{type(e).__name__}: {e}'
            if isinstance(getattr(e, 'reason', e), ssl.SSLCertVerificationError):
                break  # retrying will not fix a certificate problem
        if attempt < retries:
            time.sleep(5 * 3 ** attempt + random.uniform(0, 2))
    raise RuntimeError(last_err)


def same_page(a, b):
    norm = lambda u: u.split('?')[0].split('#')[0].rstrip('/').lower()
    return norm(a) == norm(b)


def redirect_is_rename(url, final_url, listed_urls):
    """CarDekho sometimes renames a variant's page (e.g. "2.0_l_Petrol" -> "2.0L_Petrol") and
    redirects the old link. Accept the redirect only if it stays inside the same model's
    folder and does not land on another variant that is already in the link list."""
    folder = lambda u: u.split('?')[0].rsplit('/', 1)[0].lower()
    return folder(url) == folder(final_url) and final_url.split('?')[0].lower() not in listed_urls


def scrape_one(row, out_dir, cache_dir, delay, listed_urls=frozenset()):
    log = {k: row.get(k, '') for k in ('company', 'model', 'variant', 'url', 'file_name')}
    log.update(status='', rows=0, page_heading='', final_url='', error='')
    time.sleep(delay + random.uniform(0, delay))
    try:
        html, final_url = fetch(row['url'])
    except Exception as e:
        log.update(status='fetch_failed', error=str(e))
        return log
    log['final_url'] = '' if same_page(final_url, row['url']) else final_url
    if cache_dir:
        with gzip.open(os.path.join(cache_dir, row['file_name'][:-4] + '.html.gz'), 'wt',
                       encoding='utf-8') as f:
            f.write(html)
    if log['final_url'] and not redirect_is_rename(row['url'], final_url, listed_urls):
        log.update(status='redirected', error='page redirected elsewhere; not saved')
        return log
    heading, specs = parse_specs(html)
    log.update(page_heading=heading, rows=len(specs))
    if not specs:
        log.update(status='no_specs', error='no specs table found on page')
        return log
    tmp = os.path.join(out_dir, row['file_name'] + '.part')
    with open(tmp, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(OUTPUT_COLUMNS)
        for section, name, value in specs:
            w.writerow([row['company'], row['model'], row['variant'], section, name, value])
    os.replace(tmp, os.path.join(out_dir, row['file_name']))
    log['status'] = 'ok'
    if log['final_url']:
        log['error'] = 'CarDekho renamed this page; features taken from final_url'
    return log


def write_log(path, results):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
        w.writeheader()
        w.writerows(results)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--links', default=os.path.join(DATA_DIR, 'new_variant_links.csv'))
    ap.add_argument('--out', default=os.path.join(DATA_DIR, 'new-variant-features'))
    ap.add_argument('--log', default=os.path.join(DATA_DIR, 'new_variant_features_log.csv'))
    ap.add_argument('--cache', default='', help='optional folder to keep gzipped raw HTML')
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--delay', type=float, default=1.0, help='base seconds to wait before each request')
    ap.add_argument('--limit', type=int, default=0, help='only process the first N links')
    ap.add_argument('--force', action='store_true', help='re-scrape variants that already have a CSV')
    args = ap.parse_args()

    with open(args.links, newline='', encoding='utf-8') as f:
        links = list(csv.DictReader(f))
    if args.limit:
        links = links[:args.limit]
    os.makedirs(args.out, exist_ok=True)
    if args.cache:
        os.makedirs(args.cache, exist_ok=True)

    # carry over earlier log entries so a resumed run still has a complete log
    previous = {}
    if os.path.exists(args.log):
        with open(args.log, newline='', encoding='utf-8') as f:
            previous = {r['file_name']: r for r in csv.DictReader(f)}

    results, todo = {}, []
    for row in links:
        path = os.path.join(args.out, row['file_name'])
        if not args.force and os.path.exists(path):
            prev = previous.get(row['file_name'])
            if prev and prev['status'] == 'ok':
                results[row['file_name']] = prev
            else:
                with open(path, newline='', encoding='utf-8') as f:
                    n = sum(1 for _ in f) - 1
                results[row['file_name']] = {**{k: row[k] for k in ('company', 'model', 'variant', 'url', 'file_name')},
                                             'status': 'ok', 'rows': n, 'page_heading': '',
                                             'final_url': '', 'error': 'kept existing file'}
        else:
            todo.append(row)
    print(f'{len(links)} variants: {len(results)} already saved, {len(todo)} to scrape', flush=True)

    lock = threading.Lock()
    done = 0
    order = [r['file_name'] for r in links]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        listed_urls = frozenset(r['url'].lower() for r in links)
        futures = {pool.submit(scrape_one, row, args.out, args.cache, args.delay, listed_urls): row
                   for row in todo}
        for fut in as_completed(futures):
            row = futures[fut]
            try:
                res = fut.result()
            except Exception as e:
                res = {**{k: row[k] for k in ('company', 'model', 'variant', 'url', 'file_name')},
                       'status': 'error', 'rows': 0, 'page_heading': '', 'final_url': '', 'error': repr(e)}
            with lock:
                results[res['file_name']] = res
                done += 1
                flag = '' if res['status'] == 'ok' else f"  <-- {res['status']}: {res['error']}"
                print(f"[{done}/{len(todo)}] {res['file_name']} ({res['rows']} rows){flag}", flush=True)
                if done % 25 == 0:
                    write_log(args.log, [results[k] for k in order if k in results])

    write_log(args.log, [results[k] for k in order if k in results])
    statuses = {}
    for r in results.values():
        statuses[r['status']] = statuses.get(r['status'], 0) + 1
    print('SUMMARY:', statuses, flush=True)
    return 0 if statuses.get('ok', 0) == len(links) else 1


if __name__ == '__main__':
    sys.exit(main())
