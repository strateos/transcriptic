## `transcriptic` Changelog

## Unreleased
---

## v2.0.7
Added
- `launch` command to configure and run protocols without needing to package and upload them first

## v2.0.6
Fixed
- RMSE calculation in spectrophotometry.py now reports correct RMSE
- transcriptic submit now correctly parses new autopick group
- containter attributes are correctly requested from transcriptic via spectrophotometry.py

## v2.0.5
---
Added
- List runs in a specific project using the `transcriptic runs <project_name_or_id` command

## v2.0.4
---
Added
- Enabled `analyze` and `submit` to work for Protocol objects
- Additional functionality to Container object: Use your favorite autoprotocol ContainerType functions
- Additional properties of Container object exposed: Use wellMap to return a mapping of the well indices to aliquot names

Fixed
- Set plot to default to use mpl=true (not all users have plotly credentials)


## v2.0.3
---
Added
- cost breakdown in `analyze`
- Python 3 compatibility
- use `transcriptic preview --view` to return a URL that displays the instruction cards produced by the run you want to preview (this URL expires after two hours)
- use the 'transcriptic resources <query>' CLI command to search the catalog for a resource's vendor and `id`
- `plotly` and `future` are now required

Fixed
- dataset helpers and embedding

Removed
- ipython module

## v2.0.2
---

Changed
- Refactored analysis.spectrophotometry into `Fluorescence`, `Absorbance` and `Luminescence` classes that inherit from `PlateRead`

Added
- More documentation and related configuration
- Python 3 support
- Added cost breakdown to analyze CLI

Fixed
- bug with initializing runs with Project object

## v2.0.1
---
Added
- project url and description to setup.py
- `Aliquot`, `Resource` and `Container` object types
- documentation setup and configuration

Changed
- moved `submit` from `cli` to `__init__`

Fixed
- critical bug in `submit`
- bug in `analyze`
- bug in `create_project`

## v2.0.0.
---
- migrated content from [transcriptic/runner](https://github.com/transcriptic/runner) to here, converted that code to a Python Client Library,
- CLI functionality has not changed other than renaming some commands:
    - `release` --> `build-release`
    - `upload` --> `upload-release`
    - `new-project` --> `create-project`
    - `new-package` --> `create-package`
    - `run` --> `compile`

