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


def request(url, payload, headers, *, method=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json", "Accept": "application/json",
                                                "User-Agent": "RobotNewsAgent/1.0", **headers})
    try:
        with urllib.request.urlopen(req, timeout=240, context=tls_context()) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        # Avoid logging request headers or provider responses that could contain secrets.
        raise RuntimeError(f"HTTP {exc.code} from {urllib.parse.urlsplit(url).hostname}{urllib.parse.urlsplit(url).path}") from None
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLCertVerificationError):
            raise RuntimeError(
                "TLS certificate verification failed. Install/update certificates using "
                f"'{sys.executable} -m pip install --upgrade certifi', then retry. "
                "For a custom or corporate CA, set SSL_CERT_FILE to your trusted PEM bundle."
            ) from None
        raise RuntimeError(f"Connection failed to {urllib.parse.urlsplit(url).hostname}: {exc.reason}") from None




class RobotNewsClient:
    def __init__(self, api_key, base_url=PRODUCTION_URL, page_id=None):
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("Provide a Robot News account API key")
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Provide a valid Robot News base URL")
        if page_id is not None and (not isinstance(page_id, str) or not page_id.strip()):
            raise ValueError("page_id must be a non-empty page ID")
        self.page_id = page_id
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")

    def pages(self):
        result = request(self.base_url + "/api/news-plan?list=true", None,
                         {"Authorization": "Bearer " + self.api_key})
        if not isinstance(result, dict) or not isinstance(result.get("pages"), list):
            raise RuntimeError("Robot News did not return a page list; update the server API. Deploy the website changes that add GET /api/news-plan?list=true, then rerun this check. Updating the Python scripts alone is not sufficient.")
        return result["pages"]

    def destination(self):
        query = "?" + urllib.parse.urlencode({"page_id": self.page_id}) if self.page_id else ""
        return request(self.base_url + "/api/page" + query, None,
                       {"Authorization": "Bearer " + self.api_key})

    def news_plan(self):
        query = "?" + urllib.parse.urlencode({"page_id": self.page_id}) if self.page_id else ""
        result = request(self.base_url + "/api/news-plan" + query, None,
                         {"Authorization": "Bearer " + self.api_key})
        if not result.get("configured"):
            raise ValueError("Save a news plan for the selected page in Robot News page settings.")
        if not isinstance(result.get("config"), dict) or not result.get("plan_revision"):
            raise RuntimeError("Robot News did not return a valid news plan and revision.")
        return result

    def _save_news_plan(self, settings, method):
        payload = dict(settings)
        if "page_id" not in payload:
            payload["page_id"] = self.destination()["page_id"]
        return request(self.base_url + "/api/news-plan", payload,
                       {"Authorization": "Bearer " + self.api_key}, method=method)

    def create_news_plan(self, settings):
        """Create a complete plan; fail if the destination already has one."""
        return self._save_news_plan(settings, "POST")

    def update_news_plan(self, changes):
        """Patch a plan; topics, when supplied, replace the entire array."""
        return self._save_news_plan(changes, "PATCH")

    def report_run(self, page_id, payload, *, finish=False):
        query = urllib.parse.urlencode({"page_id": page_id})
        return request(self.base_url + "/api/news-plan/runs?" + query, payload,
                       {"Authorization": "Bearer " + self.api_key},
                       method="PATCH" if finish else "POST")

    def recent_headlines(self, since):
        """Return every post title created on or after the given UTC timestamp."""
        headlines, cursor, seen = [], None, set()
        while True:
            params = {"since": since, "limit": 100}
            if self.page_id is not None:
                params["page_id"] = self.page_id
            if cursor is not None:
                params["cursor"] = cursor
            result = request(self.base_url + "/api/posts?" + urllib.parse.urlencode(params), None,
                             {"Authorization": "Bearer " + self.api_key})
            if not isinstance(result, dict) or not isinstance(result.get("posts"), list) or "nextCursor" not in result:
                raise RuntimeError("Recent post history is unavailable or the Robot News API needs updating; cannot check for duplicates")
            for post in result["posts"]:
                if not isinstance(post, dict) or not isinstance(post.get("title"), str) or not post["title"].strip():
                    raise RuntimeError("Invalid post in recent history; cannot check for duplicates")
                headlines.append(post["title"])
            cursor = result["nextCursor"]
            if cursor is None:
                return headlines
            if not isinstance(cursor, str) or not cursor or cursor in seen or not result["posts"]:
                raise RuntimeError("Recent post pagination did not advance; cannot check for duplicates")
            seen.add(cursor)

    def publish_post(self, payload):
        return request(self.base_url + "/api/posts", {**payload, **({"page_id": self.page_id} if self.page_id is not None else {})},
                       {"Authorization": "Bearer " + self.api_key})

    def publish_article(self, payload):
        return request(self.base_url + "/api/articles", {**payload, **({"page_id": self.page_id} if self.page_id is not None else {})},
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
    """Publish the standard connection-test message to production using an account key."""
    return RobotNewsClient(api_key).publish_standard_message()
