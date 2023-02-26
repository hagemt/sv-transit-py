"""test caltrain.py
"""
import os

import pytest
from click.testing import CliRunner

from modes import caltrain


def test_bearing():
    """returns North | South | Equal | Error for unknown stations"""
    sdb: caltrain.StationDB = caltrain.StationDB(data=caltrain.ZONED_STATIONS)
    home, work, other = sdb.find_stations("belmont", "hayward-park", "millbrae")

    alias, bearing = lambda s: s.alias, sdb.bearing
    assert bearing(alias(home), alias(work)) == "North"
    assert bearing(alias(work), alias(home)) == "South"
    assert bearing(alias(other), alias(other)) == "Equal"
    assert bearing("home", "work") == "Error"


SKIP_CLI = "caltrain.cli" not in os.getenv("TRANSIT_TESTS", "")


@pytest.mark.skipif(SKIP_CLI, reason="env TRANSIT_TESTS != caltrain.cli")
def test_example():
    """no args run"""
    runner = CliRunner()
    result = runner.invoke(caltrain.cli)
    assert result.exit_code == 0
    assert result.output
