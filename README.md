# Transcriptic Runner

The Transcriptic Runner is a command-line tool for interacting with the
Transcriptic API.

# Installing

```
$ git clone https://github.com/transcriptic/runner.git
$ cd runner
$ pip install .
```

# Example usage

##### Login to your Transcriptic account
Before using the runner, you'll need to log in to Transcriptic to fetch your
access key information. This will be saved in `~/.transcriptic` for future
commands.

```
$ transcriptic login
Email: sanger@transcriptic.com
Password:
Logged in as sanger@transcriptic.com (cambridge)
```

##### Analyze a protocol 
Submit a protocol to Transcriptic to check its validity.
```
$ python my_protocol.py | transcriptic analyze 
✓ Protocol analyzed
  2 instructions
  1 container
```

##### Submit a protocol to Transcriptic
```
$ python my_protocol.py | transcriptic submit --project sequencing --title "Sequencing run"
Run created: https://secure.transcriptic.com/cambridge/sequencing/r1xa043277aekj
```
