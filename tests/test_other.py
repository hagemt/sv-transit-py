"""test defaults
"""
from modes import __version__


def test_version():
    """chore: bump version"""
    assert __version__ == "0.1.2"
