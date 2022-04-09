#!/usr/bin/env python
"""caltrain.html
"""
import dataclasses as D
import datetime as DT
import json
import os
import sys
import typing as T
import warnings

from bs4 import BeautifulSoup
from requests import post

# functions to produce and extract real-time data from Caltrain
path = os.path.join(os.path.dirname(__file__), "caltrain.html")
_out = os.getenv("CALTRAIN_HTML", path)


def fix(names: T.Iterable[str]) -> T.List[str]:
    """regularize station names"""

    def fix1(name: str) -> str:
        name = name.replace("-", " ").title()
        name = name.replace("22Nd", "22nd")
        name = name.replace("Avenue", "Ave")
        name = name.replace("City", "San Francisco")
        name = name.replace("Diridon", "San Jose Dirion")
        name = name.replace("Redwood San Francisco", "Redwood City")
        name = name.replace("South", "So")
        name = name.replace("Stanford", "Stanford Stadium")
        return name

    return list(fix1(name) for name in names if name.strip())


_stn = fix(os.getenv("STATION_NAMES", "Belmont").split(","))

# valid station names:
# - San Francisco (zone 1)
# - 22nd Street
# - Bayshore
# - So San Francisco
# - San Bruno
# - Millbrae (zone 2, and BART connection)
# - Broadway (weekend only)
# - Burlingame
# - San Mateo
# - Hayward Park
# - Hillsdale
# - Belmont
# - San Carlos
# - Redwood City
# - Menlo Park (zone 3)
# - Atherton (closed Nov 2020)
# - Palo Alto
# - Stanford Stadium (football only)
# - California Ave
# - San Antonio
# - Mountain View
# - Sunnyvale
# - Lawrence (zone 4)
# - College Park
# - Santa Clara
# - San Jose Diridon
# - Tamien
# - Capitol (zone 5)
# - Blossom Hill
# - Morgan Hill (zone 6)
# - San Martin
# - Gilroy
# (from North to South)


def fetch_html(stn_name: str = _stn[0]) -> str:
    """obtain HTML from Caltrain"""
    head: T.Dict[str, str] = {
        # User-Agent not required
    }
    stn = stn_name.title()
    data = {
        "__CALLBACKID": "ctl09",
        "__CALLBACKPARAM": f"refreshStation={stn}",
        "__VIEWSTATE": "",
        "ipf-st-ip-station": stn,
    }

    url = os.getenv("POST_URL", "https://www.caltrain.com/main.html")
    res = post(url, data=data, headers=head)
    res.raise_for_status()
    txt = res.text
    with open(_out, encoding="UTF-8", mode="w") as file:
        file.write(txt)
    return txt


def now() -> str:
    """like JS"""
    return DT.datetime.utcnow().replace(microsecond=0).isoformat() + ".000Z"


@D.dataclass(repr=False)
class Trains:
    """for station, in both directions"""

    _when: str = D.field(default_factory=now)
    north: T.List[T.Tuple[str, ...]] = D.field(default_factory=list)
    south: T.List[T.Tuple[str, ...]] = D.field(default_factory=list)
    where: T.Optional[str] = None

    def __str__(self) -> str:
        return repr(self)  # want: human grep/read-able output

    def __repr__(self) -> str:
        return json.dumps(D.asdict(self), separators=(",", ":"))


CaltrainError = T.NewType("CaltrainError", str)  # worse than Exception
CaltrainTuple = T.Tuple[T.Optional[Trains], T.Optional[CaltrainError]]


class Soup(T.Protocol):
    """because mypy dumb?"""

    def find(self, *args, class_: str = "") -> BeautifulSoup:
        """types-beautifulsoup4"""

    def find_all(self, *args, class_: str = "") -> T.Iterable[BeautifulSoup]:
        """like find, but a list"""


def parse_trains(soup: Soup, stn: str = "") -> CaltrainTuple:
    """golang style (pass BeautifulSoup and station name, get Trains)"""
    table = soup.find("table", class_="ipf-caltrain-table-trains")

    if table is None:
        div = soup.find("div", "ipf-caltrain-stationselector")  # ew
        text = div.find_all(text=True, recursive=False) if div else []

        errs = [s.strip() for s in text if s and not s.startswith("<")]
        err = "; ".join(errs)[:50] or "reports no specific error message"
        return None, "Caltrain page: " + CaltrainError(err)

    both = table.find_all("table", class_="ipf-st-ip-trains-subtable")
    head = table.find("tr", class_="ipf-st-ip-trains-table-dir-tr")
    dirs = [div.text for div in head.find_all("div")]  # type: ignore

    _all = lambda t: t.find_all("tr", class_="ipf-st-ip-trains-subtable-tr")
    _txt = lambda tr: tuple(str(td.text) for td in tr.find_all("td"))
    data = dict(zip(dirs, ([_txt(tr) for tr in _all(rows)] for rows in both)))

    northbound = data.get("NORTHBOUND", [])
    southbound = data.get("SOUTHBOUND", [])
    return Trains(north=northbound, south=southbound, where=stn), None


def test():
    """ensure we can parse HTML from Caltrain"""
    with open(_out, encoding="UTF-8", mode="r") as file:
        soup = BeautifulSoup(file.read(), "html.parser")
        print(soup, file=sys.stderr)

        with warnings.catch_warnings(record=True) as group:
            for stn in _stn:
                trains, err = parse_trains(soup, stn=stn)
                if err is None:
                    print(trains)
                else:
                    warnings.warn(f"at {stn}: {err}")

            for warning in group:
                print(warning.message, file=sys.stderr)
            assert len(group) == 0, f"{len(group)} warning(s)"


if __name__ == "__main__":
    fetch_html()
    test()
