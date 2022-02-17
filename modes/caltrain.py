#!/usr/bin/env python3
'''Find next Caltrains

--- Quick setup:
brew install python && pip3 install --user beautifulsoup4 click requests
(then draft an alias or crontab for your particular use of this script)

--- USAGE: ./caltrain.py --help
'''
from collections import defaultdict, namedtuple, OrderedDict
from dataclasses import asdict, dataclass
#from types import SimpleNamespace as JSON
import datetime
import json
import os
import re

from bs4 import BeautifulSoup
import click
import requests

ORIGIN_URL = os.getenv('CT_ORIGIN_URL', 'https://www.caltrain.com')
KnownStation = namedtuple('KnownStation', 'index alias zone key url')
#loads = lambda s: json.loads(s, object_hook=lambda obj: JSON(**obj))
msnow = lambda: int(datetime.datetime.now().timestamp() * 1000)

from_key = lambda k: re.sub(r'Station|Transit Center$', '', k[5:]).strip()
def to_key(name: str, alias: str, ignore='Millbrae', suffix='Station') -> str:
    '''Converts words like "belmont" into "CALT: Belmont Station" (station key)
    Note: This "normalizes" input to title case and handles Millbrae edge case.
    '''
    if ignore is not None and ignore.casefold() == alias.casefold():
        return to_key(name, alias, ignore=None, suffix='Transit Center')
    normalize = lambda alias: alias.replace('-', ' ').title() # fragile?
    return ' '.join(['CALT:', normalize(os.getenv(name, alias)), suffix])

@dataclass(frozen=True, repr=False)
class ModeTrain:
    '''Parsed real-time data, and print-able as text or JSON
    '''
    what: str # e.g. ... Caltrain #123
    when: int # UTC milliseconds since UNIX epoch
    where: str # station alias/key

    def __repr__(self):
        ddt = str(int((self.when - msnow()) / 60000))
        return f'{self.what} in {ddt:>3s} min at {self.where}'

class StationDB(OrderedDict):
    '''Useful for understanding the relationship between two stations

    Given (zone, alias) info, deduces a key-value pair (station, URL)
    - It is feasible to lookup stations by zone, alias, station, etc.
    - Index is the position in which data was loaded, starting at #1

    Functions are provided in order to fetch real-time train data.
    '''
    def __init__(self, base=ORIGIN_URL, data=None):
        super().__init__()
        zones = OrderedDict({} if data is None else (alias, zone) for zone, alias in data)
        self._named = OrderedDict()
        self._zones = defaultdict(OrderedDict)
        for index, alias in enumerate(zones, start=1):
            zone = zones[alias]
            key = to_key('', alias)
            url = StationDB.build_url(base, key)
            k = KnownStation(index, alias, zone, key, url)
            # this station and URL is easy to discover

            self._named[key] = k
            self._zones[zone][alias] = k
            self[index] = k

    def bearing(self, one: str, two: str) -> str:
        '''returns "North" or "South" for any two distinct stations
        (returns "Error" in the case of unknown/identical stations)
        '''
        no_station = (0,)
        lhs, = self.find_stations(one, absent=no_station)
        rhs, = self.find_stations(two, absent=no_station)
        if lhs == rhs or lhs[0] == 0 or rhs[0] == 0:
            return 'Equal'
        return 'South' if lhs[0] < rhs[0] else 'North'

    def find_stations(self, *args, absent=None) -> list:
        '''returns station tuples (or singleton list if absent)
        '''
        alias = lambda k: k if k in self._named else to_key('', k)
        found = [self._named.get(alias(k), absent) for k in args]
        #print(f'--- {args} found us stations?', found)
        return found if len(found) > 0 else [absent]

    def zone_stations(self, num: int) -> dict:
        '''returns known stations in Caltrain zone #N by alias
        '''
        return self._zones[num]

    @staticmethod
    def build_url(base, raw, prefix='CALT: ', suffix='.html') -> str:
        '''URL to Caltrain real-time station page
        '''
        page = raw.replace(prefix, '').replace(' ', '') + suffix
        return '/'.join([base, 'stations', page]).lower()

    @staticmethod
    def fetch_soup(url):
        '''GET and parse HTML via URL
        '''
        res = requests.get(url, headers={
            'Accept-Language': 'en-US,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)',
        })
        res.raise_for_status()
        return BeautifulSoup(res.text, 'html.parser')

# order: most North (Zone 1) to South
ZONED_STATIONS = (
    (1, 'San Francisco'),
    (1, '22nd Street'),
    (1, 'Bayshore'),
    (1, 'South San Francisco'),
    (1, 'San Bruno'),
    (2, 'Millbrae'),
    (2, 'Broadway'),
    (2, 'Burlingame'),
    (2, 'San Mateo'),
    (2, 'Hayward Park'),
    (2, 'Hillsdale'),
    (2, 'Belmont'),
    (2, 'San Carlos'),
    (2, 'Redwood City'),
    (3, 'Menlo Park'),
    (3, 'Palo Alto'),
    (3, 'Stanford'),
    (3, 'California Avenue'),
    (3, 'San Antonio'),
    (3, 'Mountain View'),
    (3, 'Sunnyvale'),
    (4, 'Lawrence'),
    (4, 'Santa Clara'),
    (4, 'College Park'),
    (4, 'San Jose Diridon'),
    (4, 'Tamien'),
    (5, 'Capitol'),
    (5, 'Blossom Hill'),
    (6, 'Morgan Hill'),
    (6, 'San Martin'),
    (6, 'Gilroy'),
)

# change behavior using env, for now
HOME_KEY = to_key('CT_HOME', 'Belmont')
WORK_KEY = to_key('CT_WORK', 'Hayward Park')

KNOWN_STATIONS = StationDB(data=ZONED_STATIONS)
STATIONS = KNOWN_STATIONS.find_stations(HOME_KEY, WORK_KEY)
HOME_URL, WORK_URL = map(lambda ks: ks.url, STATIONS)

@click.group()
@click.pass_context
def cli(ctx, **kwargs):
    '''Scrape real-time information regarding Caltrain(s)
    '''
    ctx.ensure_object(dict)
    ctx.obj.update(kwargs)
    not_json = os.getenv('CT_FMT', 'text') != 'json'
    out = 'text' if not_json else 'json'
    now = datetime.datetime.now()
    log = os.path.basename(__file__)
    click.echo(f"--- {log} format={out} now={now}", err=True)

@cli.command()
@click.pass_context
def home(ctx, **kwargs):
    '''only trains going from Home to Work
    '''
    not_json = {**ctx.obj, **kwargs}.get('human') is True
    dump(from_key(HOME_KEY), HOME_URL, human=not_json)
    #click.echo('---', err=True)

@cli.command()
@click.pass_context
def work(ctx, **kwargs):
    '''only trains going from Work to Home
    '''
    not_json = {**ctx.obj, **kwargs}.get('human') is True
    dump(from_key(WORK_KEY), WORK_URL, human=not_json)
    #click.echo('---', err=True)

def dump(station, url, **kwargs):
    '''print Caltrains to stdout

    The "hard parts" are broken out into helper functions.
    '''
    def parse_trains(soup):
        table = soup.find('table', class_='ipf-caltrain-table-trains')
        if table is None:
            return {}
        head = table.find('tr', class_='ipf-st-ip-trains-table-dir-tr')
        dirs = map(lambda div: div.text.title()[:5], head.find_all('div'))
        both = table.find_all('table', class_='ipf-st-ip-trains-subtable')
        find_text = lambda tr: tuple(td.text for td in tr.find_all('td'))
        find_rows = lambda t: t.find_all('tr', class_='ipf-st-ip-trains-subtable-tr')
        return dict(zip(dirs, (list(find_text(tr) for tr in find_rows(t)) for t in both)))
        # data maps SOUTHBOUND or NORTHBOUND to a list of "trains" (ea. tuple of strings)

    def yield_trains(soup, now=msnow()):
        data = parse_trains(soup)
        for bearing, rows in data.items():
            for row in rows:
                #print('train:', key, ' '.join(row))
                num = row[0] # e.g. 122
                etc = row[1] # e.g. Baby Bullet
                raw = int(row[2].replace(' min.', ''))
                if raw < 2:
                    continue
                details = f'Caltrain #{num} {bearing} {etc:11s}' # neat?
                departs = now + raw * 60000 # datetime/timedelta is crazy
                yield ModeTrain(what=details, when=departs, where=station)

    # ... is --format=json is better UX?
    not_json = kwargs.get('human') is True
    def to_output(train):
        if not_json:
            return repr(train)
        data = asdict(train) # mutable
        sec = data['when'] - msnow()
        data['when'] = f'{str(int(sec / 60000)):>3s} min'
        return json.dumps(data, separators=(',', ':'))

    # main logic: fetch, parse, dump
    html = StationDB.fetch_soup(url)
    for train in yield_trains(html):
        click.echo(to_output(train))

def main(*args, **kwargs):
    '''For use with alias ct=' ~/.hagemt/transit/modes/caltrain.py'
    '''
    # note: could just use click args
    fmt = os.getenv('CT_FMT', 'text')
    end = os.getenv('CT_END', 'both')
    is_human = fmt != 'json'
    if end == 'all':
        aliases = (t[1] for t in ZONED_STATIONS) # all of them
        for station in KNOWN_STATIONS.find_stations(*aliases):
            dump(station.alias, station.url, human=is_human)
    elif end == 'both':
        dump(from_key(HOME_KEY), HOME_URL, human=is_human)
        dump(from_key(WORK_KEY), WORK_URL, human=is_human)
    elif end == 'home':
        dump(from_key(HOME_KEY), HOME_URL, human=is_human)
    elif end == 'more':
        more = 'san-francisco,belmont,hayward-park,palo-alto'
        aliases = os.getenv('CT_ALL', more).split(',') # list
        for station in KNOWN_STATIONS.find_stations(*aliases):
            dump(station.alias, station.url, human=is_human)
    elif end == 'work':
        dump(from_key(WORK_KEY), WORK_URL, human=is_human)
    else:
        cli(*args, **kwargs)

if __name__ == '__main__':
    main(obj={})
