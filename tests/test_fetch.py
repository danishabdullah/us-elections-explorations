import hashlib

import httpx
import pytest

from elections.fetch import Blocked, Fetcher


def fetcher(tmp_path, handler, robots="User-agent: *\nAllow: /\n"):
    def route(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/robots.txt":
            return httpx.Response(200, text=robots)
        return handler(req)

    return Fetcher(tmp_path, min_delay=0, client=httpx.Client(transport=httpx.MockTransport(route)))


@pytest.mark.parametrize("status", [401, 403, 405, 429, 451])
def test_block_statuses_raise_and_are_not_retried(tmp_path, status):
    calls = []

    def h(req):
        calls.append(req)
        return httpx.Response(status)

    with pytest.raises(Blocked):
        fetcher(tmp_path, h).get("https://example.org/data.csv")
    assert len(calls) == 1


def test_bot_check_page_raises(tmp_path):
    page = b"<html><head><title>Just a moment</title></head><body>cf-chl captcha</body></html>"
    with pytest.raises(Blocked):
        fetcher(tmp_path, lambda r: httpx.Response(200, content=page)).get("https://example.org/x")


def test_guestbook_gate_raises(tmp_path):
    body = b'{"status":"ERROR","message":"You may not download this file without the required Guestbook response"}'
    with pytest.raises(Blocked):
        fetcher(tmp_path, lambda r: httpx.Response(400, content=body)).get("https://example.org/f")


def test_robots_disallow_raises(tmp_path):
    with pytest.raises(Blocked):
        fetcher(tmp_path, lambda r: httpx.Response(200), robots="User-agent: *\nDisallow: /\n").get(
            "https://example.org/x"
        )


def test_download_is_cached_and_checksummed(tmp_path):
    calls = []

    def h(req):
        calls.append(req)
        return httpx.Response(200, content=b"a,b\n1,2\n")

    f = fetcher(tmp_path, h)
    md5 = hashlib.md5(b"a,b\n1,2\n").hexdigest()
    first = f.get("https://example.org/d.csv", expect_md5=md5)
    second = f.get("https://example.org/d.csv")
    assert not first.from_cache and second.from_cache and len(calls) == 1
    assert first.sha256 == hashlib.sha256(b"a,b\n1,2\n").hexdigest()


def test_checksum_mismatch_raises(tmp_path):
    with pytest.raises(ValueError):
        fetcher(tmp_path, lambda r: httpx.Response(200, content=b"x")).get("https://example.org/d", expect_md5="0" * 32)
