#!/usr/bin/env python3
"""List BART trains
- Author: hagemt (2021)
- License: MIT
"""
from collections import namedtuple
import datetime as DT
import json
import os
import sys
import typing as T
import warnings

# USAGE: env BART_END=sfia BART_FMT=json ./bart.py | jq .summary -r | sort
import click
import requests

_KEY = os.getenv("BART_KEY", "MW9S-E7SL-26DU-VV8V")  ## legacy API # nosec
_URL = os.getenv("BART_URL", "https://api.bart.gov")  # you can replace these

# real-time API response (est. time departing, etc.)
_ETD = namedtuple("_ETD", "bearing bikes cars delay color dst src summary when")


def _dump_named(*args, human=None):
    """Print BART trains leaving station soon (abbr in args)
    (note: the abbreviation ALL is valid for every station)
    """

    def fetch_json(url: str) -> T.Optional[dict]:
        try:
            res = requests.get(
                url,
                headers={
                    "User-Agent": "@hagemt/bart.py",
                },
            )
            res.raise_for_status()
            return res.json().get("root")
        except ValueError as err:
            warnings.warn(f"HTTP GET {url} bad JSON; err={err}")
            return None
        except requests.exceptions.HTTPError as err:
            warnings.warn(f"HTTP GET {url} failed; err={err}")
            return None

    def safe_color(line: str, html=None) -> T.Union[str, T.Tuple[int, ...]]:
        if html is None:
            colors = {"ORANGE": "bright_red"}  # vs. ANSI colors
            return colors[line] if line in colors else line.lower()
        chunks = [html[1:3], html[3:5], html[5:7]]  # RRGGBB
        return tuple(int(s, 16) for s in chunks)

    def yield_trains(abbr: str, root: T.Optional[dict]):
        if root is None:
            return
        for station in root.get("station", []):
            for etd in station.get("etd", []):
                for estimate in etd.get("estimate", {}):
                    source = station.get("abbr", abbr)
                    target = etd.get("abbreviation", "?")
                    # can we deduce new vs. old trains from length?
                    bearing = estimate.get("direction", "?")  # North/South
                    delay = estimate.get("delay", "1")  # in minutes
                    line = estimate.get("color", "?")  # e.g. ORANGE, ignores hexcolor
                    minutes = estimate.get("minutes", "0")  # est. departure
                    platform = estimate.get("platform", "?")  # 1-4?
                    # skip over any train that is already leaving (etd=0 minutes from now)
                    when = 0 if minutes == "Leaving" else int(minutes)
                    summary = f"{line}\t{source}#{platform} {bearing} to {target} in {when:>3}min"
                    if station.get("limited") == "1":
                        summary += " (limited)"
                    if when > 0:
                        yield _ETD(
                            **{
                                "bearing": bearing,
                                "bikes": estimate.get("bikeflag") == "1",
                                "cars": estimate.get("length", "?"),  # 1-10
                                "color": safe_color(
                                    line, html=estimate.get("hexcolor")
                                ),
                                "delay": f"{delay}min" if delay != "0" else None,
                                "dst": etd.get("destination", "?"),
                                "src": station.get("name", "?"),
                                "summary": summary,
                                "when": when,
                            }
                        )

    for abbr in map(lambda a: a.upper(), args):
        trains = []
        # http://api.bart.gov/docs/etd/etd.aspx
        url = f"{_URL}/api/etd.aspx?cmd=etd&json=y&key={_KEY}&orig={abbr}"
        for train in yield_trains(abbr, fetch_json(url)):
            trains.append(train)
            if human is True:
                click.secho(train.summary, fg=train.color)  # stable output?
            else:
                click.echo(json.dumps(train._asdict(), separators=(",", ":")))
        if not trains:
            now = DT.datetime.now()
            end = (now + DT.timedelta(days=1)).replace(hour=5, minute=0)
            ddt = int((end - now).total_seconds() / 60 % (24 * 60))  # minutes
            warnings.warn(
                "\n".join(
                    [
                        "Either you are offline, or BART isn't running; check URL:",
                        url,
                        f"NOTE: weekday trains start at 5am, which is in {ddt} min",
                    ]
                )
            )


_CLI_DEFAULTS = dict(
    default_map=dict(
        {
            None: dict(
                is_human=os.getenv("BART_FMT", "text") != "json",
                stations=os.getenv("BART_END", "ALL").split(","),
            ),
        }
    ),
)


@click.group(chain=False, context_settings=_CLI_DEFAULTS, invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Scrapes real-time information regarding BART"""
    if ctx.invoked_subcommand is None:
        defaults = _CLI_DEFAULTS.get("default_map", {})
        settings = defaults.get(None, {})
        is_human = settings.get("is_human")
        stations = settings.get("stations")
        with warnings.catch_warnings(record=True) as group:
            # http://api.bart.gov/docs/overview/abbrev.aspx
            _dump_named(*stations, human=is_human)
            for warning in group:
                msg = f"Warning: {warning.message}"
                click.secho(msg, fg="yellow", file=sys.stderr)


def main(*args, **kwargs):
    """Invokes Click"""
    cli(*args, **kwargs)


if __name__ == "__main__":
    main()
