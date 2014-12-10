# Transcriptic Runner

The Transcriptic Runner is a command-line tool for interacting with the
Transcriptic API.

# Example usage

```
$ transcriptic login
Email: sanger@transcriptic.com
Password:
Logged in as sanger@transcriptic.com (cambridge)
$ transcriptic analyze < some_autoprotocol.json
✓ Protocol analyzed
  2 instructions
  1 container
$ transcriptic submit --project sequencing --title "Sequencing run" \
    < some_autoprotocol.json
Run created: https://secure.transcriptic.com/cambridge/sequencing/r1xa043277aekj
```

# Installing

```
$ git clone git@github.com:transcriptic/runner
$ cd runner
$ pip install .
```
