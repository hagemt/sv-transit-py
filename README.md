# Python for BART and Caltrain

We may add other transit modes in future. (your contributions = welcome)

See [screenshots](#screenshots) below to understand potential use cases.

## Setup

In an executable script named `ct` or `calt` for Caltrain:

```bash
#!/usr/bin/env bash
exec "${CALT:-/path/to/caltrain.py}" "$@"
```

Put the file in your `PATH` for easy customization. For BART:

```bash
#!/usr/bin/env bash
exec "${BART_CLI:-/path/to/bart.py}" "$@"
```

The best location on macOS is `/usr/local/bin` or `/opt/...` maybe.

Another option is to clone this repo and run the `make` targets for either.

### Releases

If someone actually files a request, I may publish dists of this repo.

The overhead of releases beyond GitHub is a lot for one author/maintainer.

In future: publish to PyPi, maybe Docker images, AUR (open Issue/PRs, please)

## Usage

NOTE: BART line colors may appear differently in your terminal than mine!

Caltrain stations have names like `millbrae` plus aliases I found useful.

```bash
# simplest operation, assumes both home and work:
$ ct
Caltrain #128 South Local       in  17 min at Belmont
Caltrain #314 South Limited     in  56 min at Belmont
Caltrain #130 South Local       in  82 min at Belmont
Caltrain #311 North Limited     in   4 min at Belmont
Caltrain #129 North Local       in  42 min at Belmont
Caltrain #313 North Limited     in  64 min at Belmont
Caltrain #128 South Local       in  11 min at Hayward Park
Caltrain #130 South Local       in  75 min at Hayward Park
Caltrain #132 South Local       in 130 min at Hayward Park
Caltrain #129 North Local       in  49 min at Hayward Park
Caltrain #131 North Local       in 109 min at Hayward Park
Caltrain #133 North Local       in 167 min at Hayward Park

### advanced operation:
# calt rtt sf22 --fmt=json | jq
## ... or: pipe to grep, sort, etc.
```

Set `CALT_HOME=belmont` and/or `CALT_WORK=hayward-park` as necessary.

### Screenshots

re: Caltrain, see examples above vs. all BART departures:

![image](https://user-images.githubusercontent.com/593274/160048897-14a79534-3f13-47a3-a270-ba449522a42a.png)
