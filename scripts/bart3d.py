#!/usr/bin/env python3
"""find 3-door trains

a.k.a. Fleet of the Future (202X)
"""
import datetime as DT
import json
import os
import re
import sys
import typing as T
import warnings
from collections import namedtuple

import click
import requests as HTTP
from bs4 import BeautifulSoup

# this API key isn't a secret; BART publishes it
BART_KEY = os.getenv("BART_KEY", "MW9S-E7SL-26DU-VV8V")
BASE_URL = os.getenv("BART_URL", "https://www.bart.gov")

# every station in the system has a name and four-letter abbreviation
API_BASE = BASE_URL.replace("www", "api")  # /api/xyz.aspx
STNS_URL = f"{API_BASE}/api/stn.aspx?cmd=stns&json=y&key={BART_KEY}"


def _station_names(url=STNS_URL) -> T.Iterable[str]:
    try:
        res = HTTP.get(url, timeout=10)
        res.raise_for_status()
        root = res.json().get("root", {})
        stns = root.get("stations", {}).get("station", [])
        return [stn.get("abbr", "") for stn in stns if "abbr" in stn]
    except (HTTP.HTTPError, ValueError) as err:
        raise ValueError("failed to discover station info") from err


def _dump_named(*stations, human=False) -> None:
    """yields only Fleet of the Future trains"""
    ETD = namedtuple("ETD", "summary abbr etd on to")
    now = DT.datetime.utcnow()

    def _fetch(url: str) -> HTTP.models.Response:
        res = HTTP.get(url, timeout=10)
        res.raise_for_status()
        return res

    def _parse(abbr: str, soup: BeautifulSoup) -> T.Generator[ETD, None, None]:
        for img in soup.find_all("img", class_="rtd-fof-icon"):
            etd = img.parent.parent  # holds single estimate
            _li = etd.parent.parent  # holds train destinations
            top = _li.parent.parent  # holds platform information

            raw = re.sub(r"\s+", " ", etd.text.strip())
            if raw.startswith("Leaving"):
                continue  # too late
            leaves = raw.split(" ")[0]
            ddt = DT.timedelta(minutes=int(leaves))
            when = int((now + ddt).timestamp() * 1000)

            # subject = raw.replace(" car ", f" car, 3 door, {color} train")
            platform = top.find("h3", class_="title").text.lstrip("Platform ")
            location = _li.find("span", class_="train-line").text  # Daly City
            color = etd.find("span", class_="route-spacer")["alt"]  # RED line
            subject = f"{leaves.rjust(3)} min: {color.rjust(11)} train (new)"
            summary = f"at {abbr}#{platform} to {location:20s} in {subject}"
            yield ETD(summary, abbr, etd=when, on=platform, to=location)

    def _dumps(etd: ETD) -> str:
        if human:
            return etd.summary
        data = dict(summary=etd[0], on=etd[1], to=etd[2])
        return json.dumps(data, separators=(",", ":"))

    # the /schedules/eta?stn={stn} page uses JS to load "real-time ETD" HTML
    with warnings.catch_warnings(record=True) as group:
        for stn in stations:
            res = _fetch(f"{BASE_URL}/bart/api/rte/{stn}/1/1")
            soup = BeautifulSoup(res.text, features="html.parser")
            found: T.List[ETD] = []
            for etd in _parse(stn, soup):
                click.echo(_dumps(etd))
                found.append(etd)
            if not found:
                href = f"{BASE_URL}/schedules/eta?stn={stn}"
                warnings.warn(f"at {stn}? see: {href}")
        for warning in group:
            click.secho(str(warning.message), fg="yellow", file=sys.stderr)


def _all(*args) -> str:
    names = list(args if len(args) > 0 else _station_names())
    return ",".join(names)


_CLI_DEFAULTS = dict(
    default_map={
        None: dict(
            is_human=os.getenv("BART_FMT", "text") != "json",
            stations=os.getenv("BART_END", _all()).split(","),
        ),
    },
)


@click.group(chain=False, invoke_without_command=True)
@click.pass_context
def cli(ctx) -> None:
    """Scrapes real-time information re: new BART trains"""
    # stations: http://api.bart.gov/docs/overview/abbrev.aspx
    defaults = _CLI_DEFAULTS.get("default_map", {}).get(None, {})
    is_human = defaults.get("is_human")
    stations = defaults.get("stations")
    if ctx.invoked_subcommand is None:
        _dump_named(*stations, human=is_human)  # type: ignore


@cli.command(context_settings=dict(ignore_unknown_options=True))
@click.argument("stations", nargs=-1)
@click.option("--json", is_flag=True)
def find(stations, **options) -> None:
    """locates any Fleet of the Future (three door) trains"""
    _dump_named(*stations, human=not options.get("json"))


def main(*args, **kwargs) -> None:
    """Invokes Click"""
    cli(*args, **kwargs)


if __name__ == "__main__":
    main()
