import json
import re
import tempfile
import unittest

from email.utils import formatdate

import pytest
import requests
import responses
import transcriptic.config


try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock


class ConnectionInitTests(unittest.TestCase):
    def test_inits_valid(self):
        with tempfile.NamedTemporaryFile() as config_file:
            with open(config_file.name, "w") as f:
                json.dump(
                    {
                        "email": "somebody@transcriptic.com",
                        "token": "foobarinvalid",
                        "organization_id": "transcriptic",
                        "api_root": "http://foo:5555",
                        "analytics": True,
                        "user_id": "ufoo2",
                        "feature_groups": [
                            "can_submit_autoprotocol",
                            "can_upload_packages",
                        ],
                    },
                    f,
                )

            transcriptic.config.Connection.from_file(config_file.name)

    def test_inits_invalid(self):
        with tempfile.NamedTemporaryFile() as config_file:
            with open(config_file.name, "w") as f:
                json.dump(
                    {
                        "email": "somebody@transcriptic.com",
                        # "token": "foobarinvalid",  (missing token)
                        "organization_id": "transcriptic",
                        "api_root": "http://foo:5555",
                        "analytics": True,
                        "user_id": "ufoo2",
                        "feature_groups": [
                            "can_submit_autoprotocol",
                            "can_upload_packages",
                        ],
                    },
                    f,
                )

            # TODO(meawoppl) - assertRaisesRegexp deprecated in py3
            # Move it to assertRaisesRegex()
            with self.assertRaisesRegexp(OSError, "token"):
                transcriptic.config.Connection.from_file(config_file.name)

    def get_mocked_connection(self):
        # NOTE(meawoppl) - This could be the start of a testing pattern
        # for this module.
        class FakeReturn:
            status_code = 200

            def json(self):
                return {}

        session = transcriptic.config.initialize_default_session()
        session.put = Mock(return_value=FakeReturn())
        connection = transcriptic.config.Connection(
            email="foo@transcriptic.com",
            token="bar",
            organization_id="txid",
            api_root="https://fake.transcriptic.com",
            session=session,
        )
        return session, connection

    def test_aliquot_modify(self):
        session, connection = self.get_mocked_connection()

        aliquot_id = "23534245"
        props = {"prop1": "val1"}
        connection.modify_aliquot_properties(aliquot_id, props)
        session.put.assert_called_with(
            "https://fake.transcriptic.com/api/aliquots/23534245/modify_properties",
            json={"id": aliquot_id, "data": {"delete": [], "set": props}},
        )
        self.assertTrue(
            session.headers.get("X-Organization-Id") == connection.organization_id
        )
        self.assertTrue(
            session.headers.get("X-Organization-Id") == connection.env_args["org_id"]
        )

    def test_signing(self):
        # Set up a connection with a key from a file
        with tempfile.NamedTemporaryFile() as config_file, tempfile.NamedTemporaryFile() as key_file:
            with open(key_file.name, "w") as kf:
                kf.write(
                    "-----BEGIN RSA PRIVATE KEY-----\nMIICXAIBAAKBgQDIK/IzSkBEuwKjYQo/ri4iKTTkr+FDtJetI7dYoz0//U5z7Vbu\nZQWncDNc38wMKidf2bWA+MTSWcYVUTlivp0y98MTLPsR6oJ9RwLggA2lFlCIjmdV\nUow/MmhWg0vX/SkThxS/F5I41GTrNIU3ZVZwGbmQ8hbyKCBYtbEHJWqATwIDAQAB\nAoGAHtYmSaB2ph/pGCIq4gSDNuACNfiiSzvW4eVOqWj8Vo8/NrypV7BYXqL6RqRz\nWqxjxHBVdbjdGUqbKU2J+ZxDuwCREsxQipjq+hM9aPpgjNJg4dz6yuc5mnUdOr9M\nR+zFjnnOJx98HGjuzLDXdBNYVSZFcDWj70Fjln/z5AjBYQECQQDijaHEcvDJOUmL\nDNyAYbjK811kFGpmglQBiZ257L47IP6jgqN544siHGnI7rykt+1upGfB2q8uQSIb\njNJKKsa3AkEA4jB9PXE8EooJ/eax2UsuwXt9LAgRabFurAJtadpAeeFBIIMSwBXU\n7APMfB3cQOnBlodnyrQ56mIOWPcSdN+7KQJAHr+4aBBtq/IRkETjnK0mxqz3TQEU\nW+tueXLzLGv8ecwFo620gHOoy61tki8M/ZJVMIIx7va+dhmzBmg7loNtywJAZUdy\n/K0USfTXToIaxoJcmDQUM0AVk+7n8EtR9KDOWASdpdIq9imQYnG9ASJZuhMxJJbS\nybfzatinNfzDneOEKQJBAMLOhHHbskUuuU9oDUl8sbrsreglQuoq1hvlB1uVskpi\nqMEIXSBwxAlxwmiAQLgS4hZY+cmQ3v5hCberMaZRPZ8=\n-----END RSA PRIVATE KEY-----\n"
                )
            with open(config_file.name, "w") as f:
                json.dump(
                    {
                        "email": "somebody@transcriptic.com",
                        "token": "foobarinvalid",
                        "organization_id": "transcriptic",
                        "api_root": "http://foo:5555",
                        "analytics": True,
                        "user_id": "ufoo2",
                        "feature_groups": [
                            "can_submit_autoprotocol",
                            "can_upload_packages",
                        ],
                        "rsa_key": key_file.name,
                    },
                    f,
                )

            connection = transcriptic.config.Connection.from_file(config_file.name)

        # Test that GET signature matches the above key (given a hardcoded date header)
        get_request = requests.Request(
            "GET",
            "http://foo:5555/get",
            headers={
                "Date": formatdate(timeval=1588628873, localtime=False, usegmt=True)
            },
        )
        prepared_get = connection.session.prepare_request(get_request)
        self.assertTrue(
            prepared_get.headers["X-Organization-Id"] == connection.organization_id
        )
        self.assertTrue(
            prepared_get.headers["X-Organization-Id"] == connection.env_args["org_id"]
        )

        get_sig = prepared_get.headers["authorization"]
        self.assertEqual(
            re.search(r'keyId="(.+?)"', get_sig).group(1), "somebody@transcriptic.com"
        )
        self.assertEqual(
            re.search(r'algorithm="(.+?)"', get_sig).group(1), "rsa-sha256"
        )
        self.assertEqual(
            re.search(r'signature="(.+?)"', get_sig).group(1),
            "GfcAtyV0+CKDkxjsREXYAm6RP0WdIYaN5RamlNfIYZ7e847KAydQf2ylYIcsj9CS5BIOiBi5JBoC6n51NSbxU+kQcSv2nzSsq3rBpTFFMHUhTPdrfeHsH4IBvgMWZZHmHvyE7UXVqhLssVzMIm/oGTnprPMWiTcsKjEhe+DsQT4=",
        )
        self.assertEqual(
            set(re.search(r'headers="(.+?)"', get_sig).group(1).split(" ")),
            {"(request-target)", "date", "host"},
        )

        # Test that POST signature matches the above key (given a hardcoded body & date header)
        post_request = requests.Request(
            "POST",
            "http://foo:5555/get",
            data="Some body content",
            headers={
                "Date": formatdate(timeval=1588638873, localtime=False, usegmt=True)
            },
        )
        prepared_post = connection.session.prepare_request(post_request)

        post_sig = prepared_post.headers["authorization"]
        self.assertEqual(
            re.search(r'keyId="(.+?)"', post_sig).group(1), "somebody@transcriptic.com"
        )
        self.assertEqual(
            re.search(r'algorithm="(.+?)"', post_sig).group(1), "rsa-sha256"
        )
        self.assertEqual(
            re.search(r'signature="(.+?)"', post_sig).group(1),
            "TnixnCg4eT7nQhYQP1PNZHv5MVhHnWKf6MQb+cyS2tfw6++yuSaZS/4kz9nuvAbjZ1CsLWBKBDDIQWZqQXEjGUH/mXQ3KYDXhREyl0aDv2NgxKBcAsSooDa9nfA9zI7OeFa2dYzF81oOB4L4PDkbV3Bojw4mQYJf0eLW6FL1yTI=",
        )
        self.assertEqual(
            set(re.search(r'headers="(.+?)"', post_sig).group(1).split(" ")),
            {"(request-target)", "date", "host", "content-length", "digest"},
        )

    def test_signing_post_no_body_in_request(self):
        # Set up a connection with a key from a file
        with tempfile.NamedTemporaryFile() as config_file, tempfile.NamedTemporaryFile() as key_file:
            with open(key_file.name, "w") as kf:
                kf.write(
                    "-----BEGIN RSA PRIVATE KEY-----\nMIICXAIBAAKBgQDIK/IzSkBEuwKjYQo/ri4iKTTkr+FDtJetI7dYoz0//U5z7Vbu\nZQWncDNc38wMKidf2bWA+MTSWcYVUTlivp0y98MTLPsR6oJ9RwLggA2lFlCIjmdV\nUow/MmhWg0vX/SkThxS/F5I41GTrNIU3ZVZwGbmQ8hbyKCBYtbEHJWqATwIDAQAB\nAoGAHtYmSaB2ph/pGCIq4gSDNuACNfiiSzvW4eVOqWj8Vo8/NrypV7BYXqL6RqRz\nWqxjxHBVdbjdGUqbKU2J+ZxDuwCREsxQipjq+hM9aPpgjNJg4dz6yuc5mnUdOr9M\nR+zFjnnOJx98HGjuzLDXdBNYVSZFcDWj70Fjln/z5AjBYQECQQDijaHEcvDJOUmL\nDNyAYbjK811kFGpmglQBiZ257L47IP6jgqN544siHGnI7rykt+1upGfB2q8uQSIb\njNJKKsa3AkEA4jB9PXE8EooJ/eax2UsuwXt9LAgRabFurAJtadpAeeFBIIMSwBXU\n7APMfB3cQOnBlodnyrQ56mIOWPcSdN+7KQJAHr+4aBBtq/IRkETjnK0mxqz3TQEU\nW+tueXLzLGv8ecwFo620gHOoy61tki8M/ZJVMIIx7va+dhmzBmg7loNtywJAZUdy\n/K0USfTXToIaxoJcmDQUM0AVk+7n8EtR9KDOWASdpdIq9imQYnG9ASJZuhMxJJbS\nybfzatinNfzDneOEKQJBAMLOhHHbskUuuU9oDUl8sbrsreglQuoq1hvlB1uVskpi\nqMEIXSBwxAlxwmiAQLgS4hZY+cmQ3v5hCberMaZRPZ8=\n-----END RSA PRIVATE KEY-----\n"
                )
            with open(config_file.name, "w") as f:
                json.dump(
                    {
                        "email": "somebody@transcriptic.com",
                        "token": "foobarinvalid",
                        "organization_id": "transcriptic",
                        "api_root": "http://foo:5555",
                        "analytics": True,
                        "user_id": "ufoo2",
                        "feature_groups": [
                            "can_submit_autoprotocol",
                            "can_upload_packages",
                        ],
                        "rsa_key": key_file.name,
                    },
                    f,
                )

            connection = transcriptic.config.Connection.from_file(config_file.name)

        # Test that GET signature matches the above key (given a hardcoded date header)
        get_request = requests.Request(
            "GET",
            "http://foo:5555/get",
            headers={
                "Date": formatdate(timeval=1588628873, localtime=False, usegmt=True)
            },
        )
        prepared_get = connection.session.prepare_request(get_request)
        self.assertTrue(
            prepared_get.headers["X-Organization-Id"] == connection.organization_id
        )
        self.assertTrue(
            prepared_get.headers["X-Organization-Id"] == connection.env_args["org_id"]
        )

        get_sig = prepared_get.headers["authorization"]
        self.assertEqual(
            re.search(r'keyId="(.+?)"', get_sig).group(1), "somebody@transcriptic.com"
        )
        self.assertEqual(
            re.search(r'algorithm="(.+?)"', get_sig).group(1), "rsa-sha256"
        )
        self.assertEqual(
            re.search(r'signature="(.+?)"', get_sig).group(1),
            "GfcAtyV0+CKDkxjsREXYAm6RP0WdIYaN5RamlNfIYZ7e847KAydQf2ylYIcsj9CS5BIOiBi5JBoC6n51NSbxU+kQcSv2nzSsq3rBpTFFMHUhTPdrfeHsH4IBvgMWZZHmHvyE7UXVqhLssVzMIm/oGTnprPMWiTcsKjEhe+DsQT4=",
        )
        self.assertEqual(
            set(re.search(r'headers="(.+?)"', get_sig).group(1).split(" ")),
            {"(request-target)", "date", "host"},
        )

        # Test that POST signature matches the above key (given a hardcoded body & date header)
        post_request = requests.Request(
            "POST",
            "http://foo:5555/get",
            data=None,
            headers={
                "Date": formatdate(timeval=1588638873, localtime=False, usegmt=True)
            },
        )
        prepared_post = connection.session.prepare_request(post_request)

        post_sig = prepared_post.headers["authorization"]
        self.assertEqual(
            re.search(r'keyId="(.+?)"', post_sig).group(1), "somebody@transcriptic.com"
        )
        self.assertEqual(
            re.search(r'algorithm="(.+?)"', post_sig).group(1), "rsa-sha256"
        )
        self.assertEqual(
            re.search(r'signature="(.+?)"', post_sig).group(1),
            "leQ7TO8IYbOKouKjqbwvk5uYrkmmO64aWBxxWGDMA41Kn3k0/9r6L4XWLGmMIjSqzQmFHF8Sdtz7pCh8YaQLHzXzwY0+R43jlJGLiL7WzgzWegHsnY2NwGOdGPWbVqAP3oCmr2lQtzl+k39ySW3Tpd+t8c0+VDCYOOV/kIAISVw=",
        )
        self.assertEqual(
            set(re.search(r'headers="(.+?)"', post_sig).group(1).split(" ")),
            {"(request-target)", "date", "host", "content-length", "digest"},
        )

    @responses.activate
    def test_signing_auth_header_on_redirects(self):
        # Set up a connection with a key from a file
        with tempfile.NamedTemporaryFile() as config_file, tempfile.NamedTemporaryFile() as key_file:
            with open(key_file.name, "w") as kf:
                kf.write(
                    "-----BEGIN RSA PRIVATE KEY-----\nMIICXAIBAAKBgQDIK/IzSkBEuwKjYQo/ri4iKTTkr+FDtJetI7dYoz0//U5z7Vbu\nZQWncDNc38wMKidf2bWA+MTSWcYVUTlivp0y98MTLPsR6oJ9RwLggA2lFlCIjmdV\nUow/MmhWg0vX/SkThxS/F5I41GTrNIU3ZVZwGbmQ8hbyKCBYtbEHJWqATwIDAQAB\nAoGAHtYmSaB2ph/pGCIq4gSDNuACNfiiSzvW4eVOqWj8Vo8/NrypV7BYXqL6RqRz\nWqxjxHBVdbjdGUqbKU2J+ZxDuwCREsxQipjq+hM9aPpgjNJg4dz6yuc5mnUdOr9M\nR+zFjnnOJx98HGjuzLDXdBNYVSZFcDWj70Fjln/z5AjBYQECQQDijaHEcvDJOUmL\nDNyAYbjK811kFGpmglQBiZ257L47IP6jgqN544siHGnI7rykt+1upGfB2q8uQSIb\njNJKKsa3AkEA4jB9PXE8EooJ/eax2UsuwXt9LAgRabFurAJtadpAeeFBIIMSwBXU\n7APMfB3cQOnBlodnyrQ56mIOWPcSdN+7KQJAHr+4aBBtq/IRkETjnK0mxqz3TQEU\nW+tueXLzLGv8ecwFo620gHOoy61tki8M/ZJVMIIx7va+dhmzBmg7loNtywJAZUdy\n/K0USfTXToIaxoJcmDQUM0AVk+7n8EtR9KDOWASdpdIq9imQYnG9ASJZuhMxJJbS\nybfzatinNfzDneOEKQJBAMLOhHHbskUuuU9oDUl8sbrsreglQuoq1hvlB1uVskpi\nqMEIXSBwxAlxwmiAQLgS4hZY+cmQ3v5hCberMaZRPZ8=\n-----END RSA PRIVATE KEY-----\n"
                )
            with open(config_file.name, "w") as f:
                json.dump(
                    {
                        "email": "somebody@transcriptic.com",
                        "token": "foobarinvalid",
                        "organization_id": "transcriptic",
                        "api_root": "http://foo:5555",
                        "analytics": True,
                        "user_id": "ufoo2",
                        "feature_groups": [
                            "can_submit_autoprotocol",
                            "can_upload_packages",
                        ],
                        "rsa_key": key_file.name,
                    },
                    f,
                )

            connection = transcriptic.config.Connection.from_file(config_file.name)

        get_request = requests.Request(
            "GET",
            "http://foo:5555/get",
            headers={
                "Date": formatdate(timeval=1588628873, localtime=False, usegmt=True)
            },
        )
        prepared_get = connection.session.prepare_request(get_request)

        # Setup redirect and simulate request
        resp = requests.Response()
        resp.headers["location"] = "http://foo:5555/redirect/get"
        resp.request = prepared_get
        resp.status_code = 302
        responses.add(responses.GET, "http://foo:5555/redirect/get")

        next_resp = next(connection.session.resolve_redirects(resp, prepared_get))
        # Ensure headers are properly populated
        get_sig = next_resp.request.headers["authorization"]
        self.assertEqual(
            re.search(r'keyId="(.+?)"', get_sig).group(1), "somebody@transcriptic.com"
        )
        self.assertEqual(
            re.search(r'algorithm="(.+?)"', get_sig).group(1), "rsa-sha256"
        )
        self.assertEqual(
            re.search(r'signature="(.+?)"', get_sig).group(1),
            "DdfePPvN88mmIq9l4crfwPm80SKV/iiaBht+28iwlRd+SuuB95VJJ5M+PCD8X0gEqKlwvfYHhgXFMJybMBFS2Z9Syv4wGHpM5FxEXi57mD69kW73Whkh3ROzr6fq39CdoK06BaJnQYNtZfSg7R0fgjFUImbVScQksQrYwQ3yVF4=",
        )
        self.assertEqual(
            set(re.search(r'headers="(.+?)"', get_sig).group(1).split(" ")),
            {"(request-target)", "date", "host"},
        )

    def test_signing_auth_header_not_set_when_calling_non_api_root_endpoint(self):
        # Set up a connection with a key from a file
        with tempfile.NamedTemporaryFile() as config_file, tempfile.NamedTemporaryFile() as key_file:
            with open(key_file.name, "w") as kf:
                kf.write(
                    "-----BEGIN RSA PRIVATE KEY-----\nMIICXAIBAAKBgQDIK/IzSkBEuwKjYQo/ri4iKTTkr+FDtJetI7dYoz0//U5z7Vbu\nZQWncDNc38wMKidf2bWA+MTSWcYVUTlivp0y98MTLPsR6oJ9RwLggA2lFlCIjmdV\nUow/MmhWg0vX/SkThxS/F5I41GTrNIU3ZVZwGbmQ8hbyKCBYtbEHJWqATwIDAQAB\nAoGAHtYmSaB2ph/pGCIq4gSDNuACNfiiSzvW4eVOqWj8Vo8/NrypV7BYXqL6RqRz\nWqxjxHBVdbjdGUqbKU2J+ZxDuwCREsxQipjq+hM9aPpgjNJg4dz6yuc5mnUdOr9M\nR+zFjnnOJx98HGjuzLDXdBNYVSZFcDWj70Fjln/z5AjBYQECQQDijaHEcvDJOUmL\nDNyAYbjK811kFGpmglQBiZ257L47IP6jgqN544siHGnI7rykt+1upGfB2q8uQSIb\njNJKKsa3AkEA4jB9PXE8EooJ/eax2UsuwXt9LAgRabFurAJtadpAeeFBIIMSwBXU\n7APMfB3cQOnBlodnyrQ56mIOWPcSdN+7KQJAHr+4aBBtq/IRkETjnK0mxqz3TQEU\nW+tueXLzLGv8ecwFo620gHOoy61tki8M/ZJVMIIx7va+dhmzBmg7loNtywJAZUdy\n/K0USfTXToIaxoJcmDQUM0AVk+7n8EtR9KDOWASdpdIq9imQYnG9ASJZuhMxJJbS\nybfzatinNfzDneOEKQJBAMLOhHHbskUuuU9oDUl8sbrsreglQuoq1hvlB1uVskpi\nqMEIXSBwxAlxwmiAQLgS4hZY+cmQ3v5hCberMaZRPZ8=\n-----END RSA PRIVATE KEY-----\n"
                )
            with open(config_file.name, "w") as f:
                json.dump(
                    {
                        "email": "somebody@transcriptic.com",
                        "token": "foobarinvalid",
                        "organization_id": "transcriptic",
                        "api_root": "http://foo:5555",
                        "analytics": True,
                        "user_id": "ufoo2",
                        "feature_groups": [
                            "can_submit_autoprotocol",
                            "can_upload_packages",
                        ],
                        "rsa_key": key_file.name,
                    },
                    f,
                )

            connection = transcriptic.config.Connection.from_file(config_file.name)

        get_request = requests.Request(
            "GET",
            "http://bar:5555/get",
            headers={
                "Date": formatdate(timeval=1588628873, localtime=False, usegmt=True)
            },
        )
        prepared_get = connection.session.prepare_request(get_request)
        self.assertFalse("authorization" in prepared_get.headers)
        self.assertTrue(
            prepared_get.headers["X-Organization-Id"] == connection.organization_id
        )
        self.assertTrue(
            prepared_get.headers["X-Organization-Id"] == connection.env_args["org_id"]
        )
        self.assertTrue(prepared_get.headers["X-User-Email"] == connection.email)

    def test_signing_request_body_already_encoded(self):
        # Set up a connection with a key from a file
        with tempfile.NamedTemporaryFile() as config_file, tempfile.NamedTemporaryFile() as key_file:
            with open(key_file.name, "w") as kf:
                kf.write(
                    "-----BEGIN RSA PRIVATE KEY-----\nMIICXAIBAAKBgQDIK/IzSkBEuwKjYQo/ri4iKTTkr+FDtJetI7dYoz0//U5z7Vbu\nZQWncDNc38wMKidf2bWA+MTSWcYVUTlivp0y98MTLPsR6oJ9RwLggA2lFlCIjmdV\nUow/MmhWg0vX/SkThxS/F5I41GTrNIU3ZVZwGbmQ8hbyKCBYtbEHJWqATwIDAQAB\nAoGAHtYmSaB2ph/pGCIq4gSDNuACNfiiSzvW4eVOqWj8Vo8/NrypV7BYXqL6RqRz\nWqxjxHBVdbjdGUqbKU2J+ZxDuwCREsxQipjq+hM9aPpgjNJg4dz6yuc5mnUdOr9M\nR+zFjnnOJx98HGjuzLDXdBNYVSZFcDWj70Fjln/z5AjBYQECQQDijaHEcvDJOUmL\nDNyAYbjK811kFGpmglQBiZ257L47IP6jgqN544siHGnI7rykt+1upGfB2q8uQSIb\njNJKKsa3AkEA4jB9PXE8EooJ/eax2UsuwXt9LAgRabFurAJtadpAeeFBIIMSwBXU\n7APMfB3cQOnBlodnyrQ56mIOWPcSdN+7KQJAHr+4aBBtq/IRkETjnK0mxqz3TQEU\nW+tueXLzLGv8ecwFo620gHOoy61tki8M/ZJVMIIx7va+dhmzBmg7loNtywJAZUdy\n/K0USfTXToIaxoJcmDQUM0AVk+7n8EtR9KDOWASdpdIq9imQYnG9ASJZuhMxJJbS\nybfzatinNfzDneOEKQJBAMLOhHHbskUuuU9oDUl8sbrsreglQuoq1hvlB1uVskpi\nqMEIXSBwxAlxwmiAQLgS4hZY+cmQ3v5hCberMaZRPZ8=\n-----END RSA PRIVATE KEY-----\n"
                )
            with open(config_file.name, "w") as f:
                json.dump(
                    {
                        "email": "somebody@transcriptic.com",
                        "token": "foobarinvalid",
                        "organization_id": "transcriptic",
                        "api_root": "http://foo:5555",
                        "analytics": True,
                        "user_id": "ufoo2",
                        "feature_groups": [
                            "can_submit_autoprotocol",
                            "can_upload_packages",
                        ],
                        "rsa_key": key_file.name,
                    },
                    f,
                )

            connection = transcriptic.config.Connection.from_file(config_file.name)

        # Verify that when `json` is set in the request, the authorization header is still generated without error
        # and confirm that the request body is already encoded as bytes
        post_request = requests.Request(
            "POST",
            "http://foo:5555/get",
            json={"foo": "bar"},
            headers={
                "Date": formatdate(timeval=1588628873, localtime=False, usegmt=True)
            },
        )
        prepared_post = connection.session.prepare_request(post_request)
        self.assertTrue("authorization" in prepared_post.headers)
        self.assertTrue(
            prepared_post.headers["X-Organization-Id"] == connection.organization_id
        )
        self.assertTrue(
            prepared_post.headers["X-Organization-Id"] == connection.env_args["org_id"]
        )
        self.assertTrue(prepared_post.headers["X-User-Email"] == connection.email)
        self.assertTrue(isinstance(prepared_post.body, bytes))

        # Verify that when `data` is set in the request, the authorization header is generated without error
        # and confirm that the request body is not encoded
        post_request = requests.Request(
            "POST",
            "http://foo:5555/get",
            data={"foo": "bar"},
            headers={
                "Date": formatdate(timeval=1588628873, localtime=False, usegmt=True)
            },
        )
        prepared_post = connection.session.prepare_request(post_request)
        self.assertTrue("authorization" in prepared_post.headers)
        self.assertTrue(
            prepared_post.headers["X-Organization-Id"] == connection.organization_id
        )
        self.assertTrue(
            prepared_post.headers["X-Organization-Id"] == connection.env_args["org_id"]
        )
        self.assertTrue(prepared_post.headers["X-User-Email"] == connection.email)
        self.assertFalse(isinstance(prepared_post.body, bytes))

    def test_bearer_token(self):
        """Verify that the authorization header is set when a bearer token is provided"""

        bearer_token = (
            "Bearer eyJraWQiOiJWcmVsOE9zZ0JXaUpHeEpMeFJ4bE1UaVwvbjgyc1hwWktUaTd2UExUNFQ0T"
            "T0iLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJoMTBlM2hwajliNjc4bXMwOG8zbGlibHQ2IiwidG9r"
            "ZW5fdXNlIjoiYWNjZXNzIiwic2NvcGUiOiJ3ZWJcL2dldCB3ZWJcL3Bvc3QiLCJhdXRoX3RpbWUi"
            "OjE1OTM3MjM1NDgsImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC51cy1lYXN0LTEuYW1hem9u"
            "YXdzLmNvbVwvdXMtZWFzdC0xX1d6aEZzTGlPRyIsImV4cCI6MTU5MzcyNzE0OCwiaWF0IjoxNTkz"
            "NzIzNTQ4LCJ2ZXJzaW9uIjoyLCJqdGkiOiI4Njk5ZDEwYy05Mjg4LTQ0YmEtODIxNi01OTJjZGU3"
            "MDBhY2MiLCJjbGllbnRfaWQiOiJoMTBlM2hwajliNjc4bXMwOG8zbGlibHQ2In0.YA_yiD-x6UuB"
            "MShprUbUKuB_DO6ogCtd5srfgpJA6Ve_qsf8n19nVMmFsZBy3GxzN92P1ZXiFY99FfNPohhQtaRR"
            "hpeUkir08hgJN2bEHCJ5Ym8r9mr9mlwSG6FoiedgLaUVGwJujD9c2rcA83NEo8ayTyfCynF2AZ2p"
            "MxLHvqOYtvscGMiMzIwlZfJV301iKUVgPODJM5lpJ4iKCpOy2ByCl2_KL1uxIxgMkglpB-i7kgJc"
            "-WmYoJFoN88D89ugnEoAxNfK14N4_RyEkrLNGape9kew79nUeR6fWbVFLiGDDu25_9z-7VB-GGGk"
            "7L_Hb7YgVJ5W2FwESnkDvV1T4Q"
        )

        connection = transcriptic.Connection(
            email="somebody@transcriptic.com",
            bearer_token=bearer_token,
            organization_id="transcriptic",
            api_root="http://foo:5555",
            user_id="ufoo2",
        )

        get_request = requests.Request("GET", "http://foo:5555/get")
        prepared_get = connection.session.prepare_request(get_request)

        authorization_header_value = prepared_get.headers["authorization"]
        self.assertEqual(bearer_token, authorization_header_value)
        self.assertTrue(
            prepared_get.headers["X-Organization-Id"] == connection.organization_id
        )
        self.assertTrue(
            prepared_get.headers["X-Organization-Id"] == connection.env_args["org_id"]
        )
        self.assertTrue(prepared_get.headers["X-User-Email"] == connection.email)

    def test_bearer_token_not_set_when_calling_non_api_root_endpoint(self):
        """Verify that the authorization header is NOT set when non-API root is called"""

        bearer_token = (
            "Bearer eyJraWQiOiJWcmVsOE9zZ0JXaUpHeEpMeFJ4bE1UaVwvbjgyc1hwWktUaTd2UExUNFQ0T"
            "T0iLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJoMTBlM2hwajliNjc4bXMwOG8zbGlibHQ2IiwidG9r"
            "ZW5fdXNlIjoiYWNjZXNzIiwic2NvcGUiOiJ3ZWJcL2dldCB3ZWJcL3Bvc3QiLCJhdXRoX3RpbWUi"
            "OjE1OTM3MjM1NDgsImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC51cy1lYXN0LTEuYW1hem9u"
            "YXdzLmNvbVwvdXMtZWFzdC0xX1d6aEZzTGlPRyIsImV4cCI6MTU5MzcyNzE0OCwiaWF0IjoxNTkz"
            "NzIzNTQ4LCJ2ZXJzaW9uIjoyLCJqdGkiOiI4Njk5ZDEwYy05Mjg4LTQ0YmEtODIxNi01OTJjZGU3"
            "MDBhY2MiLCJjbGllbnRfaWQiOiJoMTBlM2hwajliNjc4bXMwOG8zbGlibHQ2In0.YA_yiD-x6UuB"
            "MShprUbUKuB_DO6ogCtd5srfgpJA6Ve_qsf8n19nVMmFsZBy3GxzN92P1ZXiFY99FfNPohhQtaRR"
            "hpeUkir08hgJN2bEHCJ5Ym8r9mr9mlwSG6FoiedgLaUVGwJujD9c2rcA83NEo8ayTyfCynF2AZ2p"
            "MxLHvqOYtvscGMiMzIwlZfJV301iKUVgPODJM5lpJ4iKCpOy2ByCl2_KL1uxIxgMkglpB-i7kgJc"
            "-WmYoJFoN88D89ugnEoAxNfK14N4_RyEkrLNGape9kew79nUeR6fWbVFLiGDDu25_9z-7VB-GGGk"
            "7L_Hb7YgVJ5W2FwESnkDvV1T4Q"
        )

        connection = transcriptic.Connection(
            email="somebody@transcriptic.com",
            bearer_token=bearer_token,
            organization_id="transcriptic",
            api_root="http://foo:5555",
            user_id="ufoo2",
        )

        get_request = requests.Request("GET", "http://bar:5555/get")
        prepared_get = connection.session.prepare_request(get_request)
        self.assertFalse("authorization" in prepared_get.headers)
        self.assertTrue(
            prepared_get.headers["X-Organization-Id"] == connection.organization_id
        )
        self.assertTrue(
            prepared_get.headers["X-Organization-Id"] == connection.env_args["org_id"]
        )
        self.assertTrue(prepared_get.headers["X-User-Email"] == connection.email)

    def test_malformed_bearer_token(self):
        """Verify that an exception is thrown when a malformed JWT bearer token is provided"""

        bearer_token = "Bearer myBigBadBearerToken"

        with pytest.raises(ValueError, match="Malformed JWT Bearer Token"):
            transcriptic.Connection(
                email="somebody@transcriptic.com",
                bearer_token=bearer_token,
                organization_id="transcriptic",
                api_root="http://foo:5555",
                user_id="ufoo2",
            )

    def test_bearer_token_supersedes_user_token(self):
        """Verify that the user token and bearer token are mutually exclusive and that
        bearer token supersedes user token"""

        user_token = "userTokenFoo"
        bearer_token = (
            "Bearer eyJraWQiOiJWcmVsOE9zZ0JXaUpHeEpMeFJ4bE1UaVwvbjgyc1hwWktUaTd2UExUNFQ0T"
            "T0iLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJoMTBlM2hwajliNjc4bXMwOG8zbGlibHQ2IiwidG9r"
            "ZW5fdXNlIjoiYWNjZXNzIiwic2NvcGUiOiJ3ZWJcL2dldCB3ZWJcL3Bvc3QiLCJhdXRoX3RpbWUi"
            "OjE1OTM3MjM1NDgsImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC51cy1lYXN0LTEuYW1hem9u"
            "YXdzLmNvbVwvdXMtZWFzdC0xX1d6aEZzTGlPRyIsImV4cCI6MTU5MzcyNzE0OCwiaWF0IjoxNTkz"
            "NzIzNTQ4LCJ2ZXJzaW9uIjoyLCJqdGkiOiI4Njk5ZDEwYy05Mjg4LTQ0YmEtODIxNi01OTJjZGU3"
            "MDBhY2MiLCJjbGllbnRfaWQiOiJoMTBlM2hwajliNjc4bXMwOG8zbGlibHQ2In0.YA_yiD-x6UuB"
            "MShprUbUKuB_DO6ogCtd5srfgpJA6Ve_qsf8n19nVMmFsZBy3GxzN92P1ZXiFY99FfNPohhQtaRR"
            "hpeUkir08hgJN2bEHCJ5Ym8r9mr9mlwSG6FoiedgLaUVGwJujD9c2rcA83NEo8ayTyfCynF2AZ2p"
            "MxLHvqOYtvscGMiMzIwlZfJV301iKUVgPODJM5lpJ4iKCpOy2ByCl2_KL1uxIxgMkglpB-i7kgJc"
            "-WmYoJFoN88D89ugnEoAxNfK14N4_RyEkrLNGape9kew79nUeR6fWbVFLiGDDu25_9z-7VB-GGGk"
            "7L_Hb7YgVJ5W2FwESnkDvV1T4Q"
        )

        with tempfile.NamedTemporaryFile() as config_file:
            with open(config_file.name, "w") as f:
                json.dump(
                    {
                        "email": "somebody@transcriptic.com",
                        "token": user_token,
                        "bearer_token": bearer_token,
                        "organization_id": "transcriptic",
                        "api_root": "http://foo:5555",
                        "analytics": True,
                        "user_id": "ufoo2",
                        "feature_groups": [
                            "can_submit_autoprotocol",
                            "can_upload_packages",
                        ],
                    },
                    f,
                )
            connection = transcriptic.config.Connection.from_file(config_file.name)

        get_request = requests.Request("GET", "http://foo:5555/get")
        prepared_get = connection.session.prepare_request(get_request)

        self.assertTrue("authorization" in prepared_get.headers)
        self.assertTrue("x-user-token" not in prepared_get.headers)
        self.assertTrue(
            connection.session.auth.token == prepared_get.headers["authorization"]
        )
        self.assertTrue(
            prepared_get.headers["X-Organization-Id"] == connection.organization_id
        )
        self.assertTrue(
            prepared_get.headers["X-Organization-Id"] == connection.env_args["org_id"]
        )
        self.assertTrue(prepared_get.headers["X-User-Email"] == connection.email)
