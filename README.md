# Transcriptic Runner

The Transcriptic Runner is a command-line tool for interacting with the
Transcriptic API to submit and analyze protocols as well as upload them as packages to Transcriptic's website.

For more information on uploading and packaging releases, see the [Transcriptic Developer Hub](http://developers.transcriptic.com/v1.0/docs/package-creation-quickstart#packaging-and-uploading)


## Installation

```
$ pip install transcriptic
```

or

```
$ git clone https://github.com/transcriptic/runner.git
$ cd runner
$ pip install .
```

to upgrade to the latest version using pip or check whether you're already up to date:
```
$ pip install transcriptic --upgrade
```


## Usage

Access help by typing `$ transcriptic --help` or `$ transcriptic [COMMAND] --help`
<p align="center"><img src="screenshots/help.png?raw=true"></p>

## Mandatory first step:
**Log in to your Transcriptic account**

**\*Before using the runner, you'll need to log in to Transcriptic to fetch your
access key information. This will be saved in `~/.transcriptic` for future
commands.**\*

<p align="center"><img src="screenshots/transcripticlogin.png?raw=true"></p>

## The Basics
###Preview Protocol Output

Previewing a protocol supplies a script with parameters supplied in the "preview" section of a `manifest.json` file.  Read more about this below.

<p align="center"><img src="screenshots/transcripticpreview.png?raw=true"></p>

###Analyze a Protocol

To check whether your Autoprotocol is valid using Transcriptic's server-side checker, pipe any script that prints Autoprotocol to STDOUT to `transcriptic analyze`:
```
$ python my_protocol.py | transcriptic analyze
✓ Protocol analyzed
  2 instructions
  1 container
```

alternatively:

<p align="center"><img src="screenshots/transcripticanalyze.png?raw=true"></p>

###Submit a Protocol to a Project

Supply a project name or id to submit a run to

<p align="center"><img src="screenshots/transcripticsubmit.png?raw=true"></p>
<p align="center"><img src="screenshots/projectpage2.png?raw=true"></p>

###Submit a Protocol in Test Mode

The `--test` flag allows a run to be submitted in test mode, meaning it will never be executed

```
$ python my_protocol.py | transcriptic submit --project "sequencing" --title "Sequencing run" --test
```

###Translate a Autoprotocol to English

Pipe any valid Autoprotocol to `transcriptic summarize` to get a summary of each step

<p align="center"><img src="screenshots/transcripticsummarize.png?raw=true"></p>

## Project Management
###List Existing Projects within Your Organization

<p align="center"><img src="screenshots/transcripticprojects.png?raw=true"></p>

###Create a New Project

<p align="center"><img src="project](screenshots/transcripticnew-project.png?raw=true"></p>

###Delete a Project

<p align="center"><img src="project](screenshots/transcripticdelete-project.png?raw=true"></p>

Projects containing runs already can only be archived:

<p align="center"><img src="project](screenshots/transcripticdelete-project-with-run.png?raw=true"></p>

## Packaging and Releasing

###Create a New Package

<p align="center"><img src="package](screenshots/transcripticnew-package.png?raw=true"></p>

###List Existing Packages

<p align="center"><img src="screenshots/transcripticpackages.png?raw=true"></p>

###Initialize a Directory With an empty `manifest.json` template

The init command creates an empty `manifest.json` file with the proper structure within the current directory.  Read below or [here](https://developers.transcriptic.com/v1.0/docs/the-manifest) to find out more about what a manifest does.   Command will prompt to overwrite if your folder already contains a file called `manifest.json`.

<p align="center"><img src="screenshots/transcripticinit.png?raw=true"></p>

###Compress All Files in Working Directory into a Release

passing a `--name` argument allows you to name your release, otherwise it will be named `release_<version from manifest>` automatically

<p align="center"><img src="screenshots/transcripticreleaseonly.png?raw=true"></p>

###Compress All Files in Working Directory into a Release and Upload to a Package

<p align="center"><img src="screenshots/transcripticrelease.png?raw=true"></p>

###Upload an Existing Release to a Package

<p align="center"><img src="screenshots/transcripticupload.jpg?raw=true"></p>


### More About Packages

The [autoprotocol-python](https://github.com/autoprotocol/autoprotocol-python) library helps you generate Autoprotocol with easy to use functions. [autoprotocol.harness](https://github.com/autoprotocol/autoprotocol-python/blob/master/autoprotocol/harness.py) parses a set of typed input parameters contained in a `manifest.json` file and passes them back to the specified script when you run `transcriptic preview` (see above).  Input types also define protocol browser UI elements on transcriptic's website.

###Example
The example below assumes the following file structure:
```
test_package/
	manifest.json
	requirements.txt
	test.py
```


A manifest.json file contains metadata about protocols required when uploading a package to Transcriptic. A package can contain many protocols but for our example it will contain just one.  The `"inputs"` stanza defines expected parameter types which translate into the proper UI elements for that type when you upload the package to Transcriptic.  Read more about the manifest file [here](http://developers.transcriptic.com/v1.0/docs/the-manifest).  The preview section serves to provide your script with hard-coded parameters and refs for local testing:

<p align="center"><img src="screenshots/manifest_json.png?raw=true"></p>

The following is what your `test.py` file would look like.  Note that there is no need to declare a Protocol object within the script or print the protocol to standard out, both of these things are taken care of by `autoprotocol.harness`.  **The `protocol_name` parameter in `autoprotocol.harness.run()` must match the name of that protocol within your manifest.json file**:

<p align="center"><img src="screenshots/test_py.png?raw=true"></p>

A requirements.txt file is necessary for any modules your code relies on to run.  In the example below, the file specifies a specific commit SHA of the [autoprotocol-python](https://github.com/autoprotocol/autoprotocol-python) library.

<p align="center"><img src="screenshots/requirements_txt.png?raw=true"></p>

A release consists of everything within the protocols_folder folder **(but do not zip the folder itself: the manifest.json file must be at the top level of the archive.)**.  You can prepare a release automatically from within a directory by using the `transcript release` command as outlined above.

