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

from unittest.mock import patch

import pytest

import mirage.workspace.workspace as workspace_module
from mirage import MountMode, Workspace
from mirage.core.http_session import PooledSession
from mirage.resource.ram import RAMResource


class _FakeSession:

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def _make_ws() -> Workspace:
    return Workspace({"/ram/": RAMResource()}, mode=MountMode.WRITE)


@pytest.mark.asyncio
async def test_workspace_owns_a_lazy_pooled_session():
    ws = _make_ws()
    try:
        assert isinstance(ws._http_session, PooledSession)
        assert ws._http_session._session is None
    finally:
        await ws.close()


@pytest.mark.asyncio
async def test_execute_binds_the_workspace_pooled_session():
    ws = _make_ws()
    captured: list[object] = []
    real_bind = workspace_module.bind_shared_session

    def _spy(provider: object) -> object:
        captured.append(provider)
        return real_bind(provider)

    try:
        with patch.object(workspace_module, "bind_shared_session", _spy):
            await ws.execute("true")
        assert captured == [ws._http_session.get]
    finally:
        await ws.close()


@pytest.mark.asyncio
async def test_ram_command_never_allocates_a_session():
    ws = _make_ws()
    try:
        await ws.execute("echo hi")
        assert ws._http_session._session is None
    finally:
        await ws.close()


@pytest.mark.asyncio
async def test_close_closes_the_pooled_session():
    ws = _make_ws()
    with patch("aiohttp.TCPConnector"), \
            patch("aiohttp.ClientSession", _FakeSession):
        session = ws._http_session.get()
    assert session.closed is False
    await ws.close()
    assert session.closed is True


@pytest.mark.asyncio
async def test_pooled_session_survives_across_commands():
    ws = _make_ws()
    try:
        holder = ws._http_session
        await ws.execute("true")
        await ws.execute("true")
        assert ws._http_session is holder
    finally:
        await ws.close()
