import base64
from email.utils import formatdate
from Crypto.Hash import SHA256
from httpsig.utils import HttpSigException
from requests.auth import AuthBase
from httpsig.requests_auth import HTTPSignatureAuth
from urllib.parse import urlparse


class StrateosSign(AuthBase):
    """Signs requests"""

    def __init__(self, email, secret, api_root):
        self.email = email
        self.secret = secret
        self.api_root = api_root

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
        if urlparse(request.url).netloc != urlparse(self.api_root).netloc:
            return request

        if "Date" not in request.headers:
            request.headers["Date"] = formatdate(
                timeval=None, localtime=False, usegmt=True
            )

        if request.method.upper() in ("PUT", "POST", "PATCH"):
            encoded_body = (
                request.body
                if isinstance(request.body, bytes)
                else request.body.encode()
            )
            digest = SHA256.new(encoded_body).digest()
            sha = base64.b64encode(digest).decode("ascii")
            request.headers["Digest"] = f"SHA-256={sha}"
            return self.body_auth(request)

        return self.auth(request)


class BearerAuth(AuthBase):
    def __init__(self, token, api_root):
        self.token = token
        self.api_root = api_root

    def __call__(self, request):
        if urlparse(request.url).netloc == urlparse(self.api_root).netloc:
            request.headers["authorization"] = self.token

        return request
