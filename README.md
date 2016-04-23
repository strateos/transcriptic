# Testing

## Overview

We use the [pytest](http://pytest.org/latest/getting-started.html) framework for writing tests. A helpful resource for a
list of supported assertions can be found [here](https://pytest.org/latest/assert.html).
We also use [tox](https://tox.readthedocs.org/en/latest/) for automating tests.

Ensure that all tests pass when you run `tox` in the main folder.
Alternatively, one can run `py.test <path_to_test>` if you are trying to test a specific module.

## Structure
Helper functions should go into the helpers folder, and autoprotocol json in the autoprotocol folder.
The `conftest.py` file contains any pytest related configurations.

## Writing API Tests
For API tests, we overwrite the base call command with a mock call that draws from the `mockDB` dictionary.
To mock responses, we use the `MockResponse` class, which basically mirrors the `Response` class from the
requests library. The three key fields to mock here are the `status_code`, `json` and `text` fields.
Similar to the `Response` object, the `status_code` corresponds to the HTML response codes (e.g. 404, 201),
the `json` method corresponds to the `json` response which is usually returned when the call is succesful.
Lastly, the `text` field is what's commonly used for displaying logs/error messages.

The `api_test` module is a nice reference for how one typically sets up responses and test.

