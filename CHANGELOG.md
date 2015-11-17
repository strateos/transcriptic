## `transcriptic` Changelog

## Unreleased
---

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

