"""CLI for BART or Caltrain
"""
import sys

from modes import bart, caltrain


def main(out=sys.stderr):
    """parent CLI"""
    cmd = sys.argv[1] if len(sys.argv) > 1 else None  # will print CLI usage
    exe = sys.argv[0] if not sys.argv[0].endswith("__main__.py") else "modes"
    usage = lambda: print(f"--- USAGE: {exe} bart|ct ...", file=out)
    if cmd is None:
        cmd = "usage"
    else:
        del sys.argv[1]

    if cmd == "teh":
        bart.main()
        caltrain.main()
    elif cmd == "ct":
        caltrain.main()
    elif cmd == "bart":
        bart.main()
    else:
        usage()


if __name__ == "__main__":
    main()
