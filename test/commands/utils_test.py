import responses

from transcriptic import commands


class TestUtils:
    @responses.activate
    def test_valid_payment_method_true(self, test_connection):
        responses.add(
            responses.GET,
            test_connection.get_route("get_payment_methods"),
            json=[{"id": "someId", "is_valid": True}],
        )
        assert commands.is_valid_payment_method(test_connection, "someId")

    @responses.activate
    def test_valid_payment_method_false(self, test_connection):
        responses.add(
            responses.GET,
            test_connection.get_route("get_payment_methods"),
            json=[{"id": "someId", "is_valid": True}],
        )
        assert not commands.is_valid_payment_method(test_connection, "invalidId")
