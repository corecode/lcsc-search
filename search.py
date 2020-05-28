import json
from typing import *

import jsonpath2.parser
import urllib3


class Fetcher:
    BASE_URL = 'https://lcsc.com/api/products/search'

    DEFAULTS = {
        'order[0][field]': 'price',
        'order[0][sort]': 'asc',
    }

    def __init__(self, attrs: Dict[str, str]):
        self.attrs = dict(self.DEFAULTS)
        self.attrs.update(attrs)
        self.http = urllib3.PoolManager()
        self.page = 1
        self.fetch_one(1) # update last_page

    def fetch_one(self, page: int):
        form = dict(self.attrs)
        form['current_page'] = str(page)
        r = self.http.request('POST', self.BASE_URL, fields=form)
        data = json.loads(r.data.decode('utf-8'))
        if not data['success']:
            raise RuntimeError(data['message'])
        self.last_page = data['result']['last_page']
        return data['result']['data']

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        while self.page <= self.last_page:
            data = self.fetch_one(self.page)
            for item in data:
                yield item
            self.page = self.page + 1


class Filter:
    def __init__(self, expr: str):
        self.expr = jsonpath2.path.Path.parse_str(expr)

    def __call__(self, data):
        matches = list(self.expr.match(data))
        return matches


def format(it: Dict[str, Any]):
    s: List[str] = []
    s.append('%s: %s, %s' % (it['info']['number'], it['info']['title'], it['package']))
    pattr = {k: v for k, v in it['attributes'].items() if v != '-' and v != '0'}
    maxattrlen = max([0] + list(len(k) for k in pattr.keys()))
    for k, v in pattr.items():
        s.append('\t%s:%s %s' % (k, ' ' * (maxattrlen - len(k)), v))
    s.append('\tprice:')
    for brk in it['price']:
        s.append('\t\t%s:\t%s' % (brk[0], brk[1]))
    return '\n'.join(s)


def main(argv: List[str]):
    import argparse
    import itertools

    parser = argparse.ArgumentParser()
    parser.add_argument('--category', type=str)
    parser.add_argument('--filter', type=Filter, default=Filter('$'))
    parser.add_argument('--page', type=int, default=1)
    parser.add_argument('--limit', type=int, default=10)
    args = parser.parse_args(argv)

    if args.limit < 0:
        args.limit = None

    f = Fetcher({'category': args.category})
    f.page = args.page
    for it in itertools.islice(filter(args.filter, f), 0, args.limit):
        print(format(it))


if __name__ == '__main__':
    import sys
    main(sys.argv[1:])
