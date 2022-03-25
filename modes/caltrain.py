#!/usr/bin/env python3
'''Find next Caltrains

--- Quick setup:
brew install python && pip3 install --user beautifulsoup4 click requests
# then draft an alias or crontab for your particular use of this script

-- USAGE: ./caltrain.py --help
- CT_END=both # vs. "home" or "work" for example (train list filter)
- CT_FMT=text # vs. json output, TODO: consider using CLI args instead
- CT_HUB='...' # major stations, e.g. SF, Millbrae, RWC, PA, MV, SJ Diridon
- CT_MINE ... # stations, incl. CT_HOME and CT_WORK aliases
- CT_URL=https://www.caltrain.com # useful for debug
^ (default values for environment variables, which you can override)

# Author: hagemt (2021)
# License: MIT
'''
from collections import defaultdict, namedtuple, OrderedDict
from dataclasses import asdict, dataclass
from datetime import datetime

import json
import os
import re

from bs4 import BeautifulSoup
import click # CLI tools
import requests # HTTP

# static data
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

_URL = os.getenv('CT_URL', 'https://www.caltrain.com')
_msnow = lambda: int(datetime.now().timestamp() * 1000)

# stations are title case, map to FQ name (starts with CALT:) plus aliases
_env_station = lambda k: re.sub(r'Station|Transit Center$', '', k[5:]).strip()
def _env_key(named: str, words: str, ignore='Millbrae', suffix='Station') -> str:
    '''Converts words, e.g. "belmont" => "CALT: Belmont Station" (fully qualified)
    Note: This "normalizes" input to title case and handles an edge case=Millbrae.
    '''
    if ignore is not None and ignore.casefold() == words.casefold():
        return _env_key(named, words, ignore=None, suffix='Transit Center')
    normalize = lambda s: s.replace('-', ' ').title() # san-mateo => San Mateo
    return ' '.join(['CALT:', normalize(os.getenv(named, words)), suffix])

# StationDB manages values of this record type
KnownStation = namedtuple('KnownStation', 'index alias zone key url')

@dataclass(frozen=True, repr=False)
class RealTime:
    '''Parsed real-time data, and print-able as text or JSON
    '''
    what: str # e.g. ... Caltrain #123
    when: int # UTC milliseconds since UNIX epoch
    where: str # station alias/key

    def __repr__(self):
        ddt = str(int((self.when - _msnow()) / 60000))
        return f'{self.what} in {ddt:>3s} min at {self.where}'

class StationDB(OrderedDict):
    '''Useful for understanding the relationship between stations

    Given (zone, alias) info, deduces a key-value pair (station, URL)
    - It is feasible to lookup stations by zone, alias, station, etc.
    - Index is the position in which data was loaded, starting at #1

    Also, functions are provided to fetch real-time Caltrain data.
    '''
    def __init__(self, base=_URL, data=None):
        super().__init__()
        _data = OrderedDict({} if data is None else (alias, zone) for zone, alias in data)
        self._zones = defaultdict(OrderedDict)
        self._named = OrderedDict()
        for index, alias in enumerate(_data, start=1):
            zone = _data[alias]
            key = _env_key('', alias)
            url = StationDB.build_url(base, key)
            k = KnownStation(index, alias, zone, key, url)
            # this station and URL is easy to discover

            self._zones[zone][alias] = k
            self._named[key] = k
            self[index] = k

    def _bearing(self, one: str, two: str) -> str:
        '''returns "North" or "South" for any two distinct stations
        (returns "Error" in the case of unknown/identical stations)
        '''
        no_station = (0,)  # sentinel value for "absent"
        lhs, = self.find_stations(one, absent=no_station)
        rhs, = self.find_stations(two, absent=no_station)
        if lhs != rhs and lhs[0] > 0 and rhs[0] > 0:
            return 'South' if lhs[0] < rhs[0] else 'North'
        return 'Equal' if lhs[0] > 0 and rhs[0] > 0 else 'Error'

    def find_stations(self, *args, absent=None) -> list:
        '''returns station tuples (or singleton list if absent)
        '''
        named = lambda k: k if k in self._named else _env_key('', k)
        found = [self._named.get(named(k), absent) for k in args]
        return found if len(found) > 0 else [absent]

    def zone_stations(self, num: int) -> dict:
        '''returns known stations in Caltrain zone #N
        '''
        return dict(self._zones[num])

    @staticmethod
    def build_url(base, raw, prefix='CALT: ', suffix='.html') -> str:
        '''URL to Caltrain real-time station page
        '''
        page = raw.replace(prefix, '').replace(' ', '') + suffix
        return '/'.join([base, 'stations', page]).lower()

    @staticmethod
    def fetch_soup(url):
        '''HTTP GET and parse HTML
        '''
        res = requests.get(url, headers={
            'Accept-Language': 'en-US,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)',
        })
        res.raise_for_status()
        return BeautifulSoup(res.text, 'html.parser')

def dump_named(*args, base=_URL, human=None):
    '''Calls dump with the proper parameters (kwargs) for each argument (simple repr)

    Strings in args are fully-qualified Caltrain stations like "san-francisco" or an alias like "sf"
    '''
    _hub = 'san-francisco,millbrae,hillsdale,redwood-city,palo-alto,mountain-view,san-jose-diridon'
    hubs = os.getenv('CT_HUB', _hub).split(',') # Baby Bullet stations (fastest type of Caltrain)
    mine = os.getenv('CT_MINE', 'san-francisco,belmont,hayward-park,palo-alto').split(',')
    home = _env_key('CT_HOME', 'Belmont') # closest station
    work = _env_key('CT_WORK', 'Hayward Park') # WeWork
    def build_aliases(data):
        _all = (t[1] for t in data)
        _sdb = StationDB(data=data)
        stations = _sdb.find_stations(home, work)
        home_url, work_url = map(lambda ks: ks.url, stations)

        alias = {
            'home': [(_env_station(home), home_url)],
            'hubs': [pair_up(stid) for stid in hubs],
            'mine': [pair_up(stid) for stid in mine],
            'work': [(_env_station(work), work_url)],
        }
        alias['both'] = alias['home'] + alias['work']
        alias['csco'] = [pair_up('san-jose-diridon')]
        alias['fair'] = [pair_up('hillsdale')]
        alias['mall'] = [pair_up('hillsdale')]
        alias['mv']   = [pair_up('mountain-view')]
        alias['pa']   = [pair_up('palo-alto')]
        alias['rwc']  = [pair_up('redwood-city')]
        alias['sf']   = [pair_up('san-francisco')]
        alias['sf22'] = [pair_up('22nd-street')]
        alias['sfo']  = [pair_up('millbrae')]
        alias['sjd']  = [pair_up('san-jose-diridon')]
        # which others make sense? (could load via config)
        alias['san-jose'] = [pair_up('san-jose-diridon')]
        alias['south-sf'] = [pair_up('south-san-francisco')]
        return alias

    def pair_up(k):
        key = _env_key('', k)
        url = StationDB.build_url(base, key)
        return (_env_station(key), url)
    aliases = build_aliases(ZONED_STATIONS)
    resolve = lambda k: aliases.get(k) or [pair_up(k)]
    for name, url in (v for vs in map(resolve, args) for v in vs):
        dump(name, url, human=human)

def dump(station, url, human=None):
    '''prints Caltrains to stdout using click.echo
    '''
    # The "hard parts" are broken out into helper functions.
    # * obtain BeautifulSoup via HTTP URL using StationDB
    # * parse raw data into north/south bound train list
    # * print each instance of real-time Caltrain data
    # should we return resolved stations/trains?
    def parse_trains(soup):
        table = soup.find('table', class_='ipf-caltrain-table-trains')
        if table is None:
            return {}
        head = table.find('tr', class_='ipf-st-ip-trains-table-dir-tr')
        dirs = map(lambda div: div.text.title()[:5], head.find_all('div'))
        both = table.find_all('table', class_='ipf-st-ip-trains-subtable')
        find_text = lambda tr: tuple(td.text for td in tr.find_all('td'))
        find_rows = lambda t: t.find_all('tr', class_='ipf-st-ip-trains-subtable-tr')
        return dict(zip(dirs, ([find_text(tr) for tr in find_rows(t)] for t in both)))
        # data dict maps SOUTHBOUND or NORTHBOUND to "trains" list (ea. tuple of strings)

    def yield_trains(soup, now=_msnow()):
        data = parse_trains(soup)
        for bearing, rows in data.items():
            for row in rows:
                num = row[0] # e.g. 122
                etc = row[1] # e.g. Baby Bullet
                raw = int(row[2].replace(' min.', ''))
                # skip "gone in < 1 minute" trains
                if raw < 2:
                    continue
                departs = now + raw * 60000
                summary = f'Caltrain #{num} {bearing} {etc:11s}'
                yield RealTime(what=summary, when=departs, where=station)

    # ... is --format=json is better UX?
    def to_output(train):
        if human is True:
            return repr(train)
        data = asdict(train) # mutable copy (hack)
        when = int((data['when'] - _msnow()) / 60000)
        data['when'] = f'{str(when):>3s} min'
        return json.dumps(data, separators=(',', ':'))

    # main logic: fetch, parse, dump
    html = StationDB.fetch_soup(url)
    for train in yield_trains(html):
        click.echo(to_output(train))

### Click commands

_CLI_DEFAULTS = dict(
    default_map=dict(
        rtt={'fmt': 'text'}
    )
)

@click.group(chain=False, context_settings=_CLI_DEFAULTS, invoke_without_command=True)
@click.pass_context
def cli(ctx, **kwargs):
    '''Scrapes real-time information regarding Caltrain(s)
    '''
    opts = {}
    opts.update(os.environ)
    opts.update(kwargs)
    if ctx.invoked_subcommand is None:
        stations = opts.get('CT_END', 'both') # home and work
        is_human = opts.get('CT_FMT', 'text') != 'json'
        dump_named(*stations.split(','), human=is_human)

@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument('stations', envvar='CT_END', nargs=-1) # CSVs
@click.option('--all-stations', default=True, is_flag=True)
@click.option('--fmt', envvar='CT_FMT')
def rtt(all_stations=None, fmt=None, stations=''):
    '''Lists departures from all/any particular station(s)
    '''
    human = fmt != 'json' # use jq for @csv and @tsv conversion
    named = stations.split(',') if isinstance(stations, str) else stations
    if len(named) == 0 and all_stations:
        args = (t[1] for t in ZONED_STATIONS)
        known_stations = StationDB(data=ZONED_STATIONS)
        for station in known_stations.find_stations(*args):
            dump(station.alias, station.url, human=human)
    else:
        dump_named(*named, human=human)

def main(*args, **kwargs):
    '''invokes Click with parameters
    '''
    cli(*args, **kwargs)

if __name__ == '__main__':
    main()
