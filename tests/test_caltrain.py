"""test caltrain.py
"""
from modes import caltrain, __version__

# pylint: disable=missing-function-docstring


def test_version():
    assert __version__ == "0.1.0"


def test_bearing():
    sdb: caltrain.StationDB = caltrain.KNOWN_STATIONS
    args = ("belmont", "hayward-park", "millbrae")
    home, work, other = sdb.find_stations(*args)
    assert sdb.bearing(home.alias, work.alias) == "North"
    assert sdb.bearing(work.alias, home.alias) == "South"
    assert sdb.bearing(other.alias, other.alias) == "Equal"
