"""test caltrain.py
"""
from modes import caltrain

# pylint: disable=missing-function-docstring, protected-access


def test_bearing():
    sdb: caltrain.StationDB = caltrain.StationDB(data=caltrain.ZONED_STATIONS)
    home, work, other = sdb.find_stations("belmont", "hayward-park", "millbrae")
    alias, bearing = lambda s: s.alias, sdb._bearing
    assert bearing(alias(home), alias(work)) == "North"
    assert bearing(alias(work), alias(home)) == "South"
    assert bearing(alias(other), alias(other)) == "Equal"
    assert bearing("home", "work") == "Error"
