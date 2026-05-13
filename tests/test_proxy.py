from types import SimpleNamespace

from security.proxy_allowlist import AllowlistAddon


def test_allowlist_loaded_from_env(monkeypatch):
    monkeypatch.setenv("TARGET_URL", "https://copilot.example.com")
    addon = AllowlistAddon()
    assert "copilot.example.com" in addon.allowed


def test_non_target_host_not_in_allowlist(monkeypatch):
    monkeypatch.setenv("TARGET_URL", "https://copilot.example.com")
    addon = AllowlistAddon()
    assert "evil.example.com" not in addon.allowed


def test_request_blocks_disallowed_host(monkeypatch):
    monkeypatch.setenv("TARGET_URL", "https://copilot.example.com")
    addon = AllowlistAddon()
    flow = SimpleNamespace(request=SimpleNamespace(pretty_host="evil.example.com"), response=None)

    addon.request(flow)

    assert flow.response is not None
    assert flow.response.status_code == 403


def test_response_blocks_external_redirect(monkeypatch):
    monkeypatch.setenv("TARGET_URL", "https://copilot.example.com")
    addon = AllowlistAddon()
    flow = SimpleNamespace(
        response=SimpleNamespace(
            status_code=302,
            headers={"location": "https://evil.example.com/path"},
        )
    )

    addon.response(flow)

    assert flow.response.status_code == 403
