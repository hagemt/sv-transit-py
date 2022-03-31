"""test bart.py
"""
import os
from click.testing import CliRunner
import pytest
from modes import bart

SKIP_CLI = "bart.cli" not in os.getenv("TRANSIT_TESTS", "")


@pytest.mark.skipif(SKIP_CLI, reason="env TRANSIT_TESTS != bart.cli")
def test_example():
    """no args run"""
    runner = CliRunner()
    result = runner.invoke(bart.cli)
    assert result.exit_code == 0
    assert result.output.endswith("min\n")
