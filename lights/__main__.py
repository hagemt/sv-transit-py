"""draw rainbows!
"""
import sys
import time

from . import lifxlan, rainbow


def main():
    """demo"""
    lan = lifxlan.LifxLAN()
    for _ in range(30):
        tiles = lan.get_tilechain_lights()
        if tiles:
            rainbow(tiles[0])
            return
        print("No tiles found; trying again in 2s...", file=sys.stderr)
        time.sleep(2)


if __name__ == "__main__":
    main()
