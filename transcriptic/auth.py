import base64

from abc import ABC
from email.utils import formatdate
from urllib.parse import urlparse

from Crypto.Hash import SHA256
from httpsig.requests_auth import HTTPSignatureAuth
from httpsig.utils import HttpSigException
from requests import Session
from requests.auth import AuthBase


class AuthSession(Session):
    """Custom Session to handle any auth specific behaviors"""

    def rebuild_auth(self, prepared_request, response):
        """
        Monkey-patches original rebuild_auth method which handles auth building
        for redirects. In cases where we're using any of our StrateosAuthBase
        classes, we want to always apply our own internal auth logic handlers.
        """
        if isinstance(self.auth, StrateosAuthBase):
            prepared_request.prepare_auth(self.auth)
        else:
            super().rebuild_auth(prepared_request, response)


class StrateosAuthBase(AuthBase, ABC):
    def __init__(self, api_root):
        self.api_root = api_root

    def is_internal_request(self, request):
        return urlparse(request.url).netloc == urlparse(self.api_root).netloc


class StrateosSign(StrateosAuthBase):
    """Signs requests"""

    def __init__(self, email, secret, api_root):
        super().__init__(api_root)
        self.email = email
        self.secret = secret

        headers = ["(request-target)", "Date", "Host"]
        body_headers = ["Digest", "Content-Length"]
        try:
            self.auth = HTTPSignatureAuth(
                key_id=self.email,
                algorithm="rsa-sha256",
                headers=headers,
                secret=self.secret,
            )
            self.body_auth = HTTPSignatureAuth(
                key_id=self.email,
                algorithm="rsa-sha256",
                headers=headers + body_headers,
                secret=self.secret,
            )
        except HttpSigException:
            raise ValueError(
                "Could not parse the specified RSA Key, ensure it "
                "is a PRIVATE key in PEM format"
            )

    def __call__(self, request):
        if not self.is_internal_request(request):
            return request

        if "Date" not in request.headers:
            request.headers["Date"] = formatdate(
                timeval=None, localtime=False, usegmt=True
            )

        if request.method.upper() in ("PUT", "POST", "PATCH"):
            encoded_body = (
                request.body
                if (isinstance(request.body, bytes) or request.body is None)
                else request.body.encode()
            )
            digest = SHA256.new(encoded_body).digest()
            sha = base64.b64encode(digest).decode("ascii")
            request.headers["Digest"] = f"SHA-256={sha}"
            return self.body_auth(request)

        return self.auth(request)


class StrateosBearerAuth(StrateosAuthBase):
    def __init__(self, token, api_root):
        super().__init__(api_root)
        self.token = token

    def __call__(self, request):
        if self.is_internal_request(request):
            request.headers["authorization"] = self.token

        return request
