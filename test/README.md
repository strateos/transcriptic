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

## Fixtures
[Pytest Fixtures](https://pytest.org/latest/fixture.html) are used through out the package to reduce the need for
duplicated code. This is also used for environment setup/teardown effects.
There are a couple of common fixtures shared throughout the test package.
- `test_api`: This sets up a test Connection and monkeypatches the api `_req_call` function with an offline/mock
equivalent and can be used in conjunction with the `response_db` fixture
- `response_db`, `json_db`: These fixtures are used for holding our MockResponse objects and Json objects respectively.

## Writing API Tests

###Background Information
For API tests, we overwrite the base call command with a mock call that draws from the `mockDB` dictionary.
To mock responses, we use the `MockResponse` class, which basically mirrors the `Response` class from the
requests library. The three key fields to mock here are the `status_code`, `json` and `text` fields.
Similar to the `Response` object, the `status_code` corresponds to the HTML response codes (e.g. 404, 201),
the `json` method corresponds to the `json` response which is usually returned when the call is succesful.
Lastly, the `text` field is what's commonly used for displaying logs/error messages.

### Example
Writing an `api test`:
1.  First define a test class if necessary (e.g. `TestAnalyze`). This should hold all tests related to the functionality
you are trying to test.
2.  Add module wide fixtures in the `conftest.py` file. For example, the `test_api` fixture is something which will we
will use for most testing and its found there.
3.  If there is a common set of setup steps you intend to do for each test function within the class, define an
initialization function and decorate it with the `@pytest.fixture(autouse=True)` decorator.
In this case, we define an `init_db` function which uses both the `json_db`  and `response_db` fixtures for
getting/loading a set of json and MockResponses.
4.  Write your test function, feeding in all the required fixtures. For example, here I would like to test the default
responses for an `analyze` call. I know I require the `test_api`, `json_db` and `response_db` fixtures, so I list them
as arguments.
5.  To test any mocked API calls, I'll need the `mockRoute` function. This mocks any `call`s made to a specific `route`
with a MockResponse object. If `max_calls` is specified, the `response` will be returned `max_calls` number of times.
Note that if the same route is mocked multiple times, responses will join a queue.
If `max_calls` is not specified, the response will be set as the default response of that route. The default response
 will then be returned when there are no more elements in the queue.
6.  Here, my route is given by `test_api.get_route('analyze_run')` and the call is `post`. So let's mock a route for testing
 404 responses.
`mockRoute(post, test_api.get_route('analyze_run'), response_db["mock404"], max_calls=1)`.
7.  To test if a 404 is indeed returned, I use the pytest syntax for checking exceptions. And I call `analyze_run` with
an invalid protocol json
    `with pytest.raises(Exception):`
        `test_api.analyze_run(json_db['invalidTransfer'])`

The final code block can be seen in the `TestAnalyze` class, in the `api_test` module
