"""Publish the Google Scholar numbers the homepage reads.

Reads the profile page directly instead of going through `scholarly`. That
package retries a throttled request rather than giving up, which is how this
job ended up sitting at Google's rate limit for the full six-hour runner
limit every night. One request, a real timeout, and a hard exit when the
numbers do not arrive -- a failed run leaves the last good data published.
"""

import json
import os
import random
import re
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# Scholar hands back non-breaking spaces and ellipses in author lists, and a
# redirected stdout on Windows defaults to the ANSI codepage -- GBK here,
# which cannot encode either. Printing the dump would then kill the run
# before a single file was written.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8', errors='replace')

SCHOLAR_ID = os.environ['GOOGLE_SCHOLAR_ID']

# pagesize=100 is the most the profile page will hand over in one go; a
# longer publication list would need &cstart= paging on top of this.
PROFILE_URL = (
    'https://scholar.google.com/citations'
    f'?user={SCHOLAR_ID}&hl=en&cstart=0&pagesize=100'
)

# Google serves the "unusual traffic" page to anything that looks automated,
# and a datacentre IP is already half of that suspicion.
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

ATTEMPTS = 4
TIMEOUT = 30


def fetch_profile():
    """Return the profile HTML, or exit non-zero so publishing is skipped."""
    problem = None
    for attempt in range(1, ATTEMPTS + 1):
        try:
            response = requests.get(PROFILE_URL, headers=HEADERS, timeout=TIMEOUT)
            # The stats table is the tell: a throttle page still answers 200.
            if response.status_code == 200 and 'gsc_rsb_std' in response.text:
                return response.text
            problem = f'HTTP {response.status_code}, no stats table (throttled?)'
        except requests.RequestException as exc:
            problem = str(exc)

        print(f'attempt {attempt}/{ATTEMPTS} failed: {problem}', file=sys.stderr)
        if attempt < ATTEMPTS:
            time.sleep(2 ** attempt + random.random() * 3)

    sys.exit(f'could not read the Scholar profile: {problem}')


def parse_cites_per_year(soup):
    """Pull the histogram under the table.

    The bars carry no year of their own; Scholar stacks them with a z-index
    that counts down from the left, so the year comes from that position.
    """
    years = [int(span.text) for span in soup.select('.gsc_g_t')]
    per_year = {}
    for bar in soup.select('a.gsc_g_a'):
        depth = re.search(r'z-index:\s*(\d+)', bar.get('style', ''))
        count = bar.select_one('.gsc_g_al')
        if not depth or not count:
            continue
        index = len(years) - int(depth.group(1))
        if 0 <= index < len(years):
            per_year[years[index]] = int(count.text)
    return per_year


def parse_publications(soup):
    """Key every paper by its author_pub_id, the id the page matches on."""
    publications = {}
    for row in soup.select('tr.gsc_a_tr'):
        link = row.select_one('a.gsc_a_at')
        if not link:
            continue
        found = re.search(
            r'citation_for_view=([\w-]+:[\w-]+)', link.get('href', ''))
        if not found:
            continue

        pub_id = found.group(1)
        cited = row.select_one('a.gsc_a_ac')
        year = row.select_one('span.gsc_a_h')
        grey = row.select('div.gs_gray')

        publications[pub_id] = {
            'author_pub_id': pub_id,
            'num_citations': int(cited.text) if cited and cited.text.strip() else 0,
            'bib': {
                'title': link.text.strip(),
                'pub_year': year.text.strip() if year else '',
                'author': grey[0].text.strip() if grey else '',
                'citation': grey[1].text.strip() if len(grey) > 1 else '',
            },
        }
    return publications


def parse(html):
    soup = BeautifulSoup(html, 'html.parser')

    # Citations / h-index / i10-index, each as an all-time and a 5-year cell.
    totals = [int(td.text) for td in soup.select('td.gsc_rsb_std')]
    if len(totals) < 6:
        sys.exit('stats table incomplete -- Scholar returned a throttle page')

    name = soup.select_one('#gsc_prf_in')
    author = {
        'scholar_id': SCHOLAR_ID,
        'name': name.text.strip() if name else '',
        'citedby': totals[0],
        'citedby5y': totals[1],
        'hindex': totals[2],
        'hindex5y': totals[3],
        'i10index': totals[4],
        'i10index5y': totals[5],
        'cites_per_year': parse_cites_per_year(soup),
        'publications': parse_publications(soup),
        'updated': str(datetime.now()),
    }

    # A parse that comes back empty means the markup moved or the page was a
    # throttle stub. Either way it must not overwrite a good file.
    if not author['citedby'] or not author['publications']:
        sys.exit('parsed no citations or no publications -- keeping the old data')

    return author


def main():
    author = parse(fetch_profile())
    print(json.dumps(author, indent=2, ensure_ascii=False))

    os.makedirs('results', exist_ok=True)
    with open('results/gs_data.json', 'w', encoding='utf-8') as outfile:
        json.dump(author, outfile, ensure_ascii=False)

    shieldio_data = {
        'schemaVersion': 1,
        'label': 'citations',
        'message': f"{author['citedby']}",
    }
    with open('results/gs_data_shieldsio.json', 'w', encoding='utf-8') as outfile:
        json.dump(shieldio_data, outfile, ensure_ascii=False)


if __name__ == '__main__':
    main()
