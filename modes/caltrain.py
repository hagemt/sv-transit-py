#!/usr/bin/env python3
"""Find next Caltrains

--- Quick setup:
brew install python && pip3 install --user beautifulsoup4 click requests
# then draft an alias or crontab for your particular use of this script

-- USAGE: ./caltrain.py --help
- CALT_END=both # vs. "home" or "work" for example (train list filter)
- CALT_FMT=text # vs. json output, TODO: consider using CLI args instead
- CALT_HUB='...' # major stations, e.g. SF, Millbrae, RWC, PA, MV, SJ Diridon
- CALT_MINE ... # stations, incl. CALT_HOME and CALT_WORK aliases
- CALT_URL=https://www.caltrain.com # useful for debug
^ (default values for environment variables, which you can override)

# Author: hagemt (2021)
# License: MIT
"""
import json
import os
import re
import sys
import typing as T
import warnings
from collections import defaultdict, namedtuple
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime

import click
import requests as HTTP
from bs4 import BeautifulSoup

# static data
# order: most North (Zone 1) to South
ZONED_STATIONS = (
    (1, "San Francisco"),
    (1, "22nd Street"),
    (1, "Bayshore"),
    (1, "South San Francisco"),
    (1, "San Bruno"),
    (2, "Millbrae"),
    (2, "Broadway"),
    (2, "Burlingame"),
    (2, "San Mateo"),
    (2, "Hayward Park"),
    (2, "Hillsdale"),
    (2, "Belmont"),
    (2, "San Carlos"),
    (2, "Redwood City"),
    (3, "Menlo Park"),
    (3, "Palo Alto"),
    # (3, "Stanford"),
    # ? No mobile status for Stanford ??
    # Old page: https://www.caltrain.com/stations/stanfordstation.html
    #
    # 2022-03-30: switched base URLs
    # - https://www.caltrain.com/stations.html
    # - to: https://www.caltrain.com/schedules/realtime/stations.html
    # (former has /stations/ path, plus $station.html vs. $station-mobile.html)
    # ! One station name in mobile version differs from full station name:
    # (3, "California Avenue"),
    (3, "California Ave"),
    (3, "San Antonio"),
    (3, "Mountain View"),
    (3, "Sunnyvale"),
    (4, "Lawrence"),
    (4, "Santa Clara"),
    (4, "College Park"),
    (4, "San Jose Diridon"),
    (4, "Tamien"),
    (5, "Capitol"),
    (5, "Blossom Hill"),
    (6, "Morgan Hill"),
    (6, "San Martin"),
    (6, "Gilroy"),
)

_URL = os.getenv("CALT_URL", "https://www.caltrain.com")
_msnow = lambda: int(datetime.now().timestamp() * 1000)

# stations are title case, map to FQ name (starts with CALT:) plus aliases
_env_station = lambda k: re.sub(r"Station|Transit Center$", "", k[5:]).strip()


def _env_key(named: str, words: str, ignore="Millbrae", suffix="Station") -> str:
    """Converts words, e.g. "belmont" => "CALT: Belmont Station" (fully qualified)
    Note: This "normalizes" input to title case and handles an edge case=Millbrae.
    """
    if ignore is not None and ignore.casefold() == words.casefold():
        return _env_key(named, words, ignore=None, suffix="Transit Center")
    normalize = lambda s: s.replace("-", " ").title()  # san-mateo => San Mateo
    return " ".join(["CALT:", normalize(os.getenv(named, words)), suffix])


# StationDB manages values of this record type
KnownStation = namedtuple("KnownStation", "index alias zone key url")


@dataclass(frozen=True, repr=False)
class RealTime:
    """Parsed real-time data, and print-able as text or JSON"""

    what: str  # e.g. ... Caltrain #123
    when: int  # UTC milliseconds since UNIX epoch
    where: str  # station alias/key

    def __repr__(self) -> str:
        ddt = str(self.relative_minutes())
        loc = self.calt_station
        return f"{self.what} in {ddt:>3s} min at {loc}"

    @property
    def calt_station(self) -> str:
        """returns a fully-qualified name for RT departure location"""
        # note: StationDB's build_url does a similar text modification
        return f"CALT: {self.where.replace('22Nd', '22nd')} Station"

    def relative_minutes(self, now=None) -> int:
        """returns number of minutes between 'now' and departure time"""
        ddt = self.when - (now or _msnow())
        return int(ddt / 60000)


class StationDB(dict):
    """Useful for understanding the relationship between stations

    Given (zone, alias) info, deduces a key-value pair (station, URL)
    - It is feasible to lookup stations by zone, alias, station, etc.
    - Index is the position in which data was loaded, starting at #1

    Also, functions are provided to fetch real-time Caltrain data.
    """

    def __init__(self, base=_URL, data=None) -> None:
        raw: T.Dict[str, int] = {}  # alias -> zone #
        for zone, alias in data or []:
            raw[alias] = zone
        self._zones = defaultdict(dict)  # type: ignore
        self._named: T.Dict[str, KnownStation] = {}
        for index, alias in enumerate(raw, start=1):
            zone = raw[alias]
            key = _env_key("", alias)
            url = StationDB.build_url(base, key)
            k = KnownStation(index, alias, zone, key, url)
            # this station and URL is easy to discover

            self._zones[zone][alias] = k
            self._named[key] = k
            self[index] = k

    def bearing(self, one: str, two: str) -> str:
        """returns "North" or "South" for any two distinct stations
        -- returns "Error" in the case of unknown stations
        -- returns "Equal" when both are the same station
        NOTE: any string that .find_stations can use is valid input
        """
        no_station = (0,)  # sentinel value for "absent"
        (lhs,) = self.find_stations(one, absent=no_station)
        (rhs,) = self.find_stations(two, absent=no_station)
        if lhs != rhs and lhs[0] > 0 and rhs[0] > 0:
            return "South" if lhs[0] < rhs[0] else "North"
        return "Equal" if lhs[0] > 0 and rhs[0] > 0 else "Error"

    def find_stations(self, *args, absent=None) -> list:
        """returns station tuples (or singleton list if absent)"""
        named = lambda k: k if k in self._named else _env_key("", k)
        found = [self._named.get(named(k), absent) for k in args]
        return found if len(found) > 0 else [absent]

    def zone_stations(self, num: int) -> dict:
        """returns known stations in Caltrain zone #N"""
        return dict(self._zones[num])

    @staticmethod
    def build_url(base, raw, prefix="CALT: ", suffix="-mobile.html") -> str:
        """URL to Caltrain real-time station page"""
        page = raw.replace(prefix, "").replace(" ", "") + suffix
        return f"{base}/schedules/realtime/stations/{page}".lower()

    @staticmethod
    def fetch_soup(url):
        """HTTP GET and parse HTML"""
        ie9 = "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)"
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml",
            "User-Agent": ie9,
        }
        res = HTTP.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        return BeautifulSoup(res.text, "html.parser")


def _dump_named(*args, base=_URL, human=None):
    """Calls dump with the proper parameters (kwargs) for each argument (simple repr)

    Strings in args are fully-qualified Caltrain stations like "san-francisco" or an alias like "sf"
    """
    _hub = "san-francisco,millbrae,hillsdale,redwood-city,palo-alto,mountain-view,san-jose-diridon"
    hubs = os.getenv("CALT_HUB", _hub)  # Baby Bullet stations (fastest Caltrain)
    mine = os.getenv("CALT_MINE", "san-francisco,belmont,hayward-park,palo-alto")
    home = _env_key("CALT_HOME", "Belmont")  # closest station
    work = _env_key("CALT_WORK", "Hayward Park")  # WeWork

    def build_aliases(data):
        _all = (t[1] for t in data)
        _sdb = StationDB(data=data)
        stations = _sdb.find_stations(home, work)
        home_url, work_url = map(lambda ks: ks.url, stations)

        alias = {
            "home": [(_env_station(home), home_url)],
            "hubs": [pair_up(stid) for stid in hubs.split(",")],
            "mine": [pair_up(stid) for stid in mine.split(",")],
            "work": [(_env_station(work), work_url)],
        }
        alias["both"] = alias["home"] + alias["work"]
        alias["csco"] = [pair_up("san-jose-diridon")]
        alias["fair"] = [pair_up("hillsdale")]
        alias["mall"] = [pair_up("hillsdale")]
        alias["mv"] = [pair_up("mountain-view")]
        alias["pa"] = [pair_up("palo-alto")]
        alias["rwc"] = [pair_up("redwood-city")]
        alias["sf"] = [pair_up("san-francisco")]
        alias["sf22"] = [pair_up("22nd-street")]
        alias["sfo"] = [pair_up("millbrae")]
        alias["sjd"] = [pair_up("san-jose-diridon")]
        # which others make sense? (could load via config)
        alias["san-jose"] = [pair_up("san-jose-diridon")]
        alias["south-sf"] = [pair_up("south-san-francisco")]
        return alias

    def pair_up(k):
        key = _env_key("", k)
        url = StationDB.build_url(base, key)
        return (_env_station(key), url)

    aliases = build_aliases(ZONED_STATIONS)
    resolve = lambda k: aliases.get(k) or [pair_up(k)]
    for name, url in (v for vs in map(resolve, args) for v in vs):
        _dump(name, url, human=human)


def _dump(station, url, human=None):
    """prints Caltrains to stdout using click.echo"""

    # The "hard parts" are broken out into helper functions.
    # * obtain BeautifulSoup via HTTP URL using StationDB
    # * parse raw data into north/south bound train list
    # * print each instance of real-time Caltrain data
    # should we return resolved stations/trains?
    def parse_trains(soup):
        table = soup.find("table", class_="ipf-caltrain-table-trains")
        if table is None:
            div = soup.find("div", "ipf-caltrain-stationselector")  # yuck!
            text = div.findAll(text=True, recursive=False) if div else []
            errs = filter(
                lambda s: s and not s.startswith("<"),  # no HTML
                (s.strip() for s in text),  # error on station page
            )
            err = "; ".join(errs)[:50] or "did not report a specific error message"
            return {}, "Caltrain page: " + err
        head = table.find("tr", class_="ipf-st-ip-trains-table-dir-tr")
        dirs = map(lambda div: div.text.title()[:5], head.find_all("div"))
        both = table.find_all("table", class_="ipf-st-ip-trains-subtable")
        find_text = lambda tr: tuple(td.text for td in tr.find_all("td"))
        find_rows = lambda t: t.find_all("tr", class_="ipf-st-ip-trains-subtable-tr")
        data = dict(zip(dirs, ([find_text(tr) for tr in find_rows(t)] for t in both)))
        # data dict maps SOUTHBOUND or NORTHBOUND to "trains" list (ea. tuple of strings)
        return data, ""

    def yield_trains(soup, now=_msnow()):
        data, err = parse_trains(soup)
        if len(data) == 0 or err:
            summary = err or "Caltrain real-time reporting error"
            yield RealTime(what=summary, when=now, where=station)
            warnings.warn(f"Open in browser: {url}")
            return
        for bearing, rows in data.items():
            for row in rows:
                num = row[0]  # e.g. 122
                etc = row[1]  # e.g. Baby Bullet
                raw = int(row[2].replace(" min.", ""))
                # skip "gone in 1 or less minute" trains
                if raw < 2:
                    continue
                departs = now + raw * 60000
                summary = f"Caltrain #{num} {bearing} {etc:11s}"
                yield RealTime(what=summary, when=departs, where=station)

    # ... --format=json is better UX?
    def to_output(train):
        if human is True:
            return repr(train)
        data = asdict(train)  # hacked on properties:
        data["when_minutes"] = train.relative_minutes()
        data["where"] = train.calt_station
        return json.dumps(data, separators=(",", ":"))

    # main logic: fetch, parse, dump
    html = StationDB.fetch_soup(url)
    for train in yield_trains(html):
        click.echo(to_output(train))


### Click commands

_CLI_DEFAULTS = dict(default_map=dict(rtt={"fmt": "text"}))


@contextmanager
def warnings_appended():
    """prints all warnings at the end of output

    e.g. with append_warnings(): logic()
    """
    with warnings.catch_warnings(record=True) as group:
        yield  # runs the CLI logic
        for warning in group:
            click.secho(str(warning.message), fg="yellow", file=sys.stderr)


@click.group(chain=False, context_settings=_CLI_DEFAULTS, invoke_without_command=True)
@click.pass_context
def cli(ctx, **kwargs):
    """Scrapes real-time information regarding Caltrain(s)"""
    opts: T.Dict[str, str] = {}
    opts.update(os.environ)
    opts.update(kwargs)
    if ctx.invoked_subcommand is None:
        stations = opts.get("CALT_END", "both")  # home and work
        is_human = opts.get("CALT_FMT", "text") != "json"
        with warnings_appended():
            _dump_named(*stations.split(","), human=is_human)


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("stations", envvar="CALT_END", nargs=-1)  # CSVs
@click.option("--all-stations", default=True, is_flag=True)
@click.option("--fmt", envvar="CALT_FMT")
def rtt(all_stations=None, fmt=None, stations=""):
    """Lists departures from all/any particular station(s)"""
    human = fmt != "json"  # use jq for @csv and @tsv conversion
    named = stations.split(",") if isinstance(stations, str) else stations
    if len(named) == 0 and all_stations:
        args = (t[1] for t in ZONED_STATIONS)
        known_stations = StationDB(data=ZONED_STATIONS)
        for station in known_stations.find_stations(*args):
            with warnings_appended():
                _dump(station.alias, station.url, human=human)
    else:
        with warnings_appended():
            _dump_named(*named, human=human)


def main(*args, **kwargs):
    """invokes Click with parameters"""
    cli(*args, **kwargs)


if __name__ == "__main__":
    main()
