from __future__ import annotations

try:
    from mitmproxy import http

    MITMPROXY_AVAILABLE = True
except ImportError:
    MITMPROXY_AVAILABLE = False
    http = None
