# Caltrain

Other transit modes in future

## Setup

In an executable script named `ct` for Caltrain:

```bash
#!/usr/bin/env bash
exec "${CT:-/path/to/caltrain.py}" "$@"
```

Put the file in your `PATH` for easy customization.

### Usage

Caltrain stations have names like `.

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
# env CT_FMT=json CT_END=work ct | jq
## ... or: pipe to grep, sort, etc.
```

Set `CT_HOME=belmont` and/or `CT_WORK=hayward-park` as necessary.
