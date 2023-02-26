#!/usr/bin/env python
"""run --help on modes.*
"""
import sys

import modes


def main():
    """dump CLI help"""
    cli_modes = []
    for mode in dir(modes):
        mod = getattr(modes, mode)
        if mode.startswith("_") or not hasattr(mod, "cli"):
            continue

        cli = getattr(mod, "cli")
        if callable(cli):
            print(f"--- found {mod.__file__} --help", file=sys.stderr)
            cli(["--help"], obj={}, standalone_mode=False)
            cli_modes.append(cli)
    print(f"--- found {len(cli_modes)} modes", file=sys.stderr)


if __name__ == "__main__":
    # CLI:
    main()
