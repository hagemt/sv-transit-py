#!/usr/bin/env python3
"""find 3-door trains
"""
from collections import namedtuple
import datetime as DT
import json
import os
import re
import sys
import typing as T
import warnings

from bs4 import BeautifulSoup
import click
import requests

BASE_URL = os.getenv("BART_URL", "https://www.bart.gov")

API_BASE = BASE_URL.replace("www", "api")  # /api/etd.aspx
BART_KEY = os.getenv("BART_KEY", "MW9S-E7SL-26DU-VV8V")

STNS_URL = f"{API_BASE}/api/stn.aspx?cmd=stns&json=y&key={BART_KEY}"
STN_ROOT = requests.get(STNS_URL).json().get("root", {}).get("stations", {})
STATIONS: T.Dict[str, str] = {
    stn.get("abbr"): stn.get("name") for stn in STN_ROOT.get("station", [])
}


def _dump_named(*stations, human=False):
    """yields only Fleet of the Future trains"""
    ETD = namedtuple("ETD", "summary abbr etd on to")
    now = DT.datetime.utcnow()

    def _fetch(url: str) -> requests.models.Response:
        res = requests.get(url)
        res.raise_for_status()
        return res

    def _parse(abbr: str, soup: BeautifulSoup):
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

    def _dumps(fotf: ETD) -> str:
        if human:
            return fotf.summary
        data = dict(summary=fotf[0], on=fotf[1], to=fotf[2])
        return json.dumps(data, separators=(",", ":"))

    # the /schedules/eta?stn={stn} page uses JS to poll real-time HTML
    for stn in stations:
        url = f"{BASE_URL}/bart/api/rte/{stn}/1/1"
        res = _fetch(url)
        soup = BeautifulSoup(res.text, "html.parser")
        found = []
        for train in _parse(stn, soup):
            click.echo(_dumps(train))
            found.append(train)
        if not found:
            warnings.warn(f"At {stn}? URL: {BASE_URL}/schedules/eta?stn={stn}")


def _all(*args) -> str:
    names = list(args if len(args) > 0 else STATIONS.keys())
    return ",".join(names)


_CLI_DEFAULTS = dict(
    default_map=dict(
        {
            None: dict(
                is_human=os.getenv("BART_FMT", "text") != "json",
                stations=os.getenv("BART_END", _all()).split(","),
            ),
        }
    ),
)


@click.group(chain=False, invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Scrapes real-time information re: new BART trains"""
    # stations: http://api.bart.gov/docs/overview/abbrev.aspx
    defaults = _CLI_DEFAULTS.get("default_map", {}).get(None, {})
    is_human = defaults.get("is_human")
    stations = defaults.get("stations")
    if ctx.invoked_subcommand is None:
        with warnings.catch_warnings(record=True) as group:
            _dump_named(*stations, human=is_human)
            for warning in group:
                click.secho(warning.message, fg="yellow", file=sys.stderr)


@cli.command(context_settings=dict(ignore_unknown_options=True))
@click.argument("stations", nargs=-1)
@click.option("--json", is_flag=True)
def fof(stations, **options):
    """find Fleet of the Future (three door) trains"""
    _dump_named(*stations, human=not options.get("json"))


def main(*args, **kwargs):
    """Invokes Click"""
    cli(*args, **kwargs)


if __name__ == "__main__":
    main()
