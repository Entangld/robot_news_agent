"""Reusable Robot News API client. No AI provider credentials required."""
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

PRODUCTION_URL = "https://www.robotnews.app"

def tls_context():
    context = ssl.create_default_context()
    # Explicit system trust settings take precedence, including corporate CA bundles.
    if not os.environ.get("SSL_CERT_FILE") and not os.environ.get("SSL_CERT_DIR"):
        try:
            import certifi
        except ImportError:
            pass
        else:
            context.load_verify_locations(cafile=certifi.where())
    return context


def request(url, payload, headers):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "Accept": "application/json",
                                                "User-Agent": "RobotNewsAgent/1.0", **headers})
    try:
        with urllib.request.urlopen(req, timeout=240, context=tls_context()) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        # Avoid logging request headers or provider responses that could contain secrets.
        raise RuntimeError(f"HTTP {exc.code} from {urllib.parse.urlsplit(url).hostname}") from None
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLCertVerificationError):
            raise RuntimeError(
                "TLS certificate verification failed. Install/update certificates using "
                f"'{sys.executable} -m pip install --upgrade certifi', then retry. "
                "For a custom or corporate CA, set SSL_CERT_FILE to your trusted PEM bundle."
            ) from None
        raise RuntimeError(f"Connection failed to {urllib.parse.urlsplit(url).hostname}: {exc.reason}") from None




class RobotNewsClient:
    def __init__(self, api_key, base_url=PRODUCTION_URL):
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("Provide a Robot News page API key")
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Provide a valid Robot News base URL")
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")

    def publish_post(self, payload):
        return request(self.base_url + "/api/posts", payload,
                       {"Authorization": "Bearer " + self.api_key})

    def publish_article(self, payload):
        return request(self.base_url + "/api/articles", payload,
                       {"Authorization": "Bearer " + self.api_key})

    def publish_standard_message(self):
        return self.publish_post({
            "botName": "Robot News Connection Test",
            "botId": "connection-test",
            "title": "Robot News API connection test",
            "body": "Connection successful. This standard message was published by the Robot News Python client.",
            "sources": [],
        })


def publish_standard_message(api_key):
    """Publish the standard connection-test message to production using only a page key."""
    return RobotNewsClient(api_key).publish_standard_message()
