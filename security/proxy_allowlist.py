import datetime
import json
import os
from urllib.parse import urlparse

from mitmproxy import http
from mitmproxy.http import HTTPFlow


def _load_allowlist() -> set[str]:
    target = os.environ.get("TARGET_URL", "")
    if not target:
        return set()

    parsed = urlparse(target)
    return {parsed.hostname} if parsed.hostname else set()


class AllowlistAddon:
    def __init__(self) -> None:
        self.allowed = _load_allowlist()

    def request(self, flow: HTTPFlow) -> None:
        host = flow.request.pretty_host
        if host not in self.allowed:
            flow.response = http.Response.make(
                403,
                f"Blocked: host '{host}' not in allowlist. Registered target: {self.allowed}",
                {"Content-Type": "text/plain"},
            )
            print(
                json.dumps(
                    {
                        "event": "proxy_block",
                        "blocked_host": host,
                        "allowed": list(self.allowed),
                        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
                    }
                )
            )

    def response(self, flow: HTTPFlow) -> None:
        if flow.response.status_code in (301, 302, 307, 308):
            location = flow.response.headers.get("location", "")
            parsed = urlparse(location)
            if parsed.hostname and parsed.hostname not in self.allowed:
                flow.response = http.Response.make(
                    403,
                    f"Blocked redirect to '{parsed.hostname}'",
                    {"Content-Type": "text/plain"},
                )


addons = [AllowlistAddon()]
