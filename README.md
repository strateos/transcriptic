# Transcriptic Runner

The Transcriptic Runner is a command-line tool for interacting with the
Transcriptic API.

## Installing

```
$ git clone https://github.com/transcriptic/runner.git
$ cd runner
$ pip install .
```

## Example usage

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

## Using transcriptic.runner with autoprotocol.harness and a manifest.json file

The [autoprotocol-python](https://github.com/autoprotocol/autoprotocol-python) library allows you to generate protocols in Autoprotocol with easy to use functions.  [autoprotocol.harness](https://github.com/autoprotocol/autoprotocol-python/blob/master/autoprotocol/harness.py) can be used to pass parameters to those protocols from the preview within a manifest file. 

#### Example
The example below assumes the following file structure:
```
protocols_folder/
  manifest.json
  requirements.txt
  my_protocols/
    __init__.py
    sample_protocol.py
```

A manifest.json file is used in order to upload protocols along with their metadata as a package to secure.transcriptic.com/<your organization>/protocols.  They can contain many protocols but for our example it will contain just one:
```
{
  "version": "1.0.0",
  "format": "python",
  "license": "MIT",
  "protocols":[{
    "name": "SampleProtocol",
    "command_string": "python -m my_protocols.sample_protocol",
    "preview":{
        "refs":{
          "sample_plate":{
            "type": "96-pcr",
            "discard": true
          }
        },
        "parameters":{
          "source_sample": "sample_plate/A1"
          "dest_sample": "sample_plate/A2"
          "transfer_vol": "5:microliter"
        }
    },
    "inputs": {
      "source_sample": "aliquot",
      "dest_sample": "aliquot",
      "transfer_vol": "aliquot"
    },
    "dependencies": []
  }
  ]
}

```

The following is what your sample_protocol.py file would look like.  Note that there is no need to declare a Protocol object within the script or print the protocol to standard out, both of these things are taken care of by autoprotocol.harness.  The `protocol_name` declared in autoprotocol.harnes.run() must match the name of that protocol within your manifest.json file:
```
def sample_protocol(protocol, params):
  protocol.transfer(params["source_sample"].set_volume("100:microliter"), 
                    params["dest_sample"], params["transfer_vol"])
  
if __name__ == __main__:
  from autoprotocol.harness import run
  run(sample_protocol, protocol_name="SampleProtocol")
```
To preview the protocol's output on the command line: 
```
$ transcriptic preview SampleProtocol
```
To submit the resulting protocol to transcriptic or analyze it, pipe that result to submit or analyze as above. 
```
$ transcriptic preview SampleProtocol | transcriptic analyze
```
When you're ready to upload a package to Transcriptic, make sure to include the version of autoprotocol and any other packages you might have used in your requirements.txt file:
```
autoprotocol=2.0.1
```

A release consists of everything within the protocols_folder folder (but do not zip the folder itself, such that the manifest.json file is at the top level of the resulting archive) 

for more information on uploading and packaging releases click [here](http://developers.transcriptic.com/v1.0/docs/package-quickstart#packaging-and-uploading)
