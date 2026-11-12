"""How the Wikimedia Commons set was collected (for reference; to get the same images use fetch_lists.py).

    python harness/crawl_commons.py <folder> [category=Code_128]

Takes the JPEG files of the category (API imageinfo with a copy scaled to
1920 px) and writes <folder>/commons_<n>.jpg and meta.csv
(file;title;url;license). There is no markup: the truth is the code given by
at least two of four sources — zxing-cpp, ZBar, an early run of our reader and
the file name (truth/commons-c128.csv; codes given by one source only are in
the `unsure` column and count neither as correct nor as foreign). Licences
differ per file (column `license`).
"""
import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = 'barcode-1d-benchmark/1.0 (+https://github.com/libscanner/barcode-1d-benchmark)'
API = 'https://commons.wikimedia.org/w/api.php'


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main(out, category='Code_128'):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    q = {'action': 'query', 'generator': 'categorymembers', 'gcmtitle': f'Category:{category}', 'gcmtype': 'file',
         'gcmlimit': 500, 'prop': 'imageinfo', 'iiprop': 'url|extmetadata', 'iiurlwidth': 1920, 'format': 'json'}
    pages = json.loads(get(API + '?' + urllib.parse.urlencode(q))).get('query', {}).get('pages', {})
    with open(out / 'meta.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['file', 'title', 'url', 'license'])
        n = 0
        for p in sorted(pages.values(), key=lambda p: p['title']):
            if not p['title'].lower().endswith(('.jpg', '.jpeg')):
                continue
            if 'imageinfo' not in p:   # the API returns scaled copies for at most 50 files per request
                one = {'action': 'query', 'titles': p['title'], 'prop': 'imageinfo', 'iiprop': 'url|extmetadata',
                       'iiurlwidth': 1920, 'format': 'json'}
                p = next(iter(json.loads(get(API + '?' + urllib.parse.urlencode(one)))['query']['pages'].values()))
                time.sleep(0.5)
            ii = p['imageinfo'][0]
            lic = ii.get('extmetadata', {}).get('LicenseShortName', {}).get('value', '')
            name = f'commons_{n:03d}.jpg'
            try:
                (out / name).write_bytes(get(ii.get('thumburl') or ii['url']))
            except Exception as e:
                print('skipped', p['title'], e)
                continue
            w.writerow([name, p['title'], ii['descriptionurl'], lic])
            n += 1
            time.sleep(0.5)
    print('images', n)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'Code_128')
