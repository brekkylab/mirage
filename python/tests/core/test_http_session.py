# ========= Copyright 2026 @ Strukto.AI All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2026 @ Strukto.AI All Rights Reserved. =========

import time
from unittest.mock import patch

import pytest

from mirage.core.google._client import TokenManager, google_get
from mirage.core.google.config import GoogleConfig
from mirage.core.http_session import current_http_session, shared_http_session
from mirage.core.slack._client import slack_get, slack_post
from mirage.resource.slack.config import SlackConfig


class _FakeResp:

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    async def __aenter__(self) -> "_FakeResp":
        return self

    async def __aexit__(self, *_: object) -> bool:
        return False

    async def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        return None


class _FakeSession:
    instances: list["_FakeSession"] = []

    def __init__(self, *args: object, **kwargs: object) -> None:
        _FakeSession.instances.append(self)
        self.closed = False
        self.requests: list[tuple[str, str]] = []

    def get(self, url: str, **_: object) -> _FakeResp:
        self.requests.append(("GET", url))
        return _FakeResp({"ok": True})

    def post(self, url: str, **_: object) -> _FakeResp:
        self.requests.append(("POST", url))
        return _FakeResp({"ok": True})

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *_: object) -> bool:
        await self.close()
        return False

    async def close(self) -> None:
        self.closed = True


class _FakeConnector:
    instances: list["_FakeConnector"] = []

    def __init__(self, *args: object, **kwargs: object) -> None:
        _FakeConnector.instances.append(self)


@pytest.fixture(autouse=True)
def _reset_counters():
    _FakeSession.instances.clear()
    _FakeConnector.instances.clear()
    yield


@pytest.fixture
def _fake_aiohttp():
    with patch("aiohttp.ClientSession", _FakeSession), \
            patch("aiohttp.TCPConnector", _FakeConnector):
        yield


def _slack_config() -> SlackConfig:
    return SlackConfig(token="xoxb-test")


def _token_manager() -> TokenManager:
    tm = TokenManager(GoogleConfig(client_id="cid", refresh_token="rt"))
    tm._access_token = "tok"
    tm._expires_at = time.time() + 9999
    return tm


@pytest.mark.asyncio
async def test_default_mode_creates_a_session_per_call(_fake_aiohttp):
    config = _slack_config()
    for _ in range(5):
        await slack_get(config, "conversations.list")
    assert len(_FakeSession.instances) == 5
    assert all(s.closed for s in _FakeSession.instances)


@pytest.mark.asyncio
async def test_shared_mode_reuses_one_session_and_connector(_fake_aiohttp):
    config = _slack_config()
    async with shared_http_session():
        for _ in range(5):
            await slack_get(config, "conversations.list")
    assert len(_FakeSession.instances) == 1
    assert len(_FakeConnector.instances) == 1
    assert len(_FakeSession.instances[0].requests) == 5


@pytest.mark.asyncio
async def test_shared_session_pools_across_providers(_fake_aiohttp):
    config = _slack_config()
    tm = _token_manager()
    async with shared_http_session():
        await slack_get(config, "conversations.list")
        await slack_post(config, "chat.postMessage", {"text": "hi"})
        await google_get(tm, "https://example/drive/v3/files")
    assert len(_FakeSession.instances) == 1
    assert _FakeSession.instances[0].requests == [
        ("GET", "https://slack.com/api/conversations.list"),
        ("POST", "https://slack.com/api/chat.postMessage"),
        ("GET", "https://example/drive/v3/files"),
    ]


@pytest.mark.asyncio
async def test_borrowed_session_is_not_closed_by_client_calls(_fake_aiohttp):
    config = _slack_config()
    async with shared_http_session() as session:
        await slack_get(config, "conversations.list")
        assert session.closed is False
    assert session.closed is True


@pytest.mark.asyncio
async def test_current_http_session_binding_lifecycle(_fake_aiohttp):
    assert current_http_session() is None
    async with shared_http_session() as session:
        assert current_http_session() is session
    assert current_http_session() is None
