"""A polite, cached HTTP fetcher that stops at blocks instead of working around them.

Rules it enforces:
- robots.txt is honored for every host.
- One request at a time per host, with a minimum delay between requests.
- 401/403/405/407/429/451 responses and bot-check pages raise `Blocked`; they are never retried or routed around.
- Only network errors and 5xx responses are retried, with backoff.
- Every download is cached under data/raw with its URL, retrieval time and SHA-256, so a build never refetches
  unless asked to.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

USER_AGENT = "us-elections-explorations/0.1 (public election data; non-commercial)"
BLOCK_STATUSES = {401, 403, 405, 407, 429, 451}
BOT_CHECK_MARKERS = (b"captcha", b"cf-chl", b"challenge-platform", b"are you a robot", b"verify you are human")


class Blocked(Exception):
    """The site refused automated access. Record it and use another legitimate source; don't retry."""


@dataclass(frozen=True, slots=True)
class Download:
    url: str
    path: Path
    sha256: str
    retrieved_at: str
    from_cache: bool


class Fetcher:
    def __init__(self, raw_dir: Path, *, min_delay: float = 1.0, client: httpx.Client | None = None) -> None:
        self.raw_dir = raw_dir
        self.min_delay = min_delay
        self.client = client or httpx.Client(
            headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=httpx.Timeout(60.0, connect=15.0)
        )
        self._last: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser] = {}

    def _paths(self, url: str, name: str | None = None) -> tuple[Path, Path]:
        host = urlparse(url).netloc
        if name:  # a readable file name for files worth keeping in the repo
            body = self.raw_dir / host / name
            return body, body.with_name(body.name + ".meta.json")
        base = self.raw_dir / host / hashlib.sha256(url.encode()).hexdigest()[:16]
        return base.with_suffix(".bin"), base.with_suffix(".json")

    def _allowed(self, url: str) -> bool:
        u = urlparse(url)
        root = f"{u.scheme}://{u.netloc}"
        if root not in self._robots:
            rp = RobotFileParser()
            try:
                r = self.client.get(root + "/robots.txt")
                rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            except httpx.HTTPError:
                rp.parse([])
            self._robots[root] = rp
        return self._robots[root].can_fetch(USER_AGENT, url)

    def _wait(self, host: str) -> None:
        gap = time.monotonic() - self._last.get(host, 0.0)
        if gap < self.min_delay:
            time.sleep(self.min_delay - gap)
        self._last[host] = time.monotonic()

    def post_json(self, url: str, payload: dict) -> dict:
        """POST a JSON body (e.g. a Dataverse guestbook response) and return the JSON reply. Never cached."""
        if not self._allowed(url):
            raise Blocked(f"robots.txt disallows {url}")
        self._wait(urlparse(url).netloc)
        r = self.client.post(url, json=payload)
        if r.status_code in BLOCK_STATUSES:
            raise Blocked(f"{url} returned HTTP {r.status_code}")
        r.raise_for_status()
        return r.json()

    def get(
        self,
        url: str,
        *,
        refresh: bool = False,
        expect_md5: str | None = None,
        cache_key: str | None = None,
        name: str | None = None,
    ) -> Download:
        """Fetch url. cache_key names the cache entry when url is one-off (e.g. a signed URL with a token);
        name stores the body under a readable file name."""
        key = cache_key or url
        body_path, meta_path = self._paths(key, name)
        if body_path.exists() and meta_path.exists() and not refresh:
            meta = json.loads(meta_path.read_text())
            return Download(key, body_path, meta["sha256"], meta["retrieved_at"], from_cache=True)
        if not self._allowed(url):
            raise Blocked(f"robots.txt disallows {url}")
        host = urlparse(url).netloc
        r: httpx.Response | None = None
        for attempt in range(4):
            self._wait(host)
            try:
                r = self.client.get(url)
            except httpx.TransportError:
                if attempt == 3:
                    raise
                time.sleep(2**attempt)
                continue
            if r.status_code in BLOCK_STATUSES:
                raise Blocked(f"{url} returned HTTP {r.status_code}")
            if r.status_code == 400 and b"guestbook" in r.content[:2000].lower():
                raise Blocked(f"{url} requires a Dataverse guestbook response (a form for a person to fill in)")
            if r.status_code >= 500 and attempt < 3:
                time.sleep(2**attempt)
                continue
            r.raise_for_status()
            head = r.content[:4096].lower()
            if b"<html" in head and any(m in head for m in BOT_CHECK_MARKERS):
                raise Blocked(f"{url} served a bot check")
            break
        assert r is not None
        if expect_md5 and hashlib.md5(r.content).hexdigest() != expect_md5:
            raise ValueError(f"{url}: checksum does not match the publisher's MD5 {expect_md5}")
        sha = hashlib.sha256(r.content).hexdigest()
        if body_path.exists() and meta_path.exists():
            old = json.loads(meta_path.read_text())
            if old["sha256"] == sha:  # unchanged since first retrieval: keep the files (and the repo) as they are
                return Download(key, body_path, sha, old["retrieved_at"], from_cache=False)
        now = datetime.now(UTC).isoformat(timespec="seconds")
        body_path.parent.mkdir(parents=True, exist_ok=True)
        body_path.write_bytes(r.content)
        meta_path.write_text(json.dumps({"url": key, "sha256": sha, "retrieved_at": now, "status": r.status_code}))
        return Download(key, body_path, sha, now, from_cache=False)
