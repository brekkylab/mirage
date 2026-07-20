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

import contextvars
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

import aiohttp

# Matched to Node/undici's default dispatcher so both runtimes pool the same:
# limit 0 = unlimited (undici connections=null), 4s keep-alive (undici 4e3),
# no DNS cache (undici resolves per new connection).
DEFAULT_CONNECTION_LIMIT = 0
DEFAULT_KEEPALIVE_TIMEOUT = 4.0
DEFAULT_TTL_DNS_CACHE = 0

SessionProvider = Callable[[], aiohttp.ClientSession]

_shared: contextvars.ContextVar[SessionProvider | None] = \
    contextvars.ContextVar("mirage_shared_http_session", default=None)


def new_pooled_session(
    limit: int = DEFAULT_CONNECTION_LIMIT,
    keepalive_timeout: float = DEFAULT_KEEPALIVE_TIMEOUT,
    ttl_dns_cache: int = DEFAULT_TTL_DNS_CACHE,
) -> aiohttp.ClientSession:
    """Create a keep-alive pooled session.

    Must be called inside the event loop that will run the requests and be
    closed on that same loop.

    Args:
        limit (int): max simultaneous connections in the pool.
        keepalive_timeout (float): seconds an idle connection is kept alive.
        ttl_dns_cache (int): seconds a resolved host is cached.

    Returns:
        aiohttp.ClientSession: a session over a keep-alive TCPConnector.
    """
    connector = aiohttp.TCPConnector(
        limit=limit,
        keepalive_timeout=keepalive_timeout,
        ttl_dns_cache=ttl_dns_cache,
    )
    return aiohttp.ClientSession(connector=connector)


class PooledSession:
    """Lazily owns one keep-alive session, reused across calls.

    The session is created on the first get() -- which happens inside a real
    client call, hence inside the running loop -- so a workspace that never
    touches an HTTP backend never allocates a connector. Closed once on
    aclose() (workspace teardown), on the same loop that created it.
    """

    def __init__(
        self,
        limit: int = DEFAULT_CONNECTION_LIMIT,
        keepalive_timeout: float = DEFAULT_KEEPALIVE_TIMEOUT,
        ttl_dns_cache: int = DEFAULT_TTL_DNS_CACHE,
    ) -> None:
        self._limit = limit
        self._keepalive_timeout = keepalive_timeout
        self._ttl_dns_cache = ttl_dns_cache
        self._session: aiohttp.ClientSession | None = None

    def get(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = new_pooled_session(self._limit,
                                               self._keepalive_timeout,
                                               self._ttl_dns_cache)
        return self._session

    async def aclose(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None


def current_http_session() -> aiohttp.ClientSession | None:
    """Return the shared session bound to the current context, if any.

    Called by client _session_scope helpers right before a request, so the
    bound provider creating the session here is intentional (lazy).

    Returns:
        aiohttp.ClientSession | None: the shared session when a provider is
            bound and yields an open session, else None (callers then fall
            back to a per-call session).
    """
    provider = _shared.get()
    if provider is None:
        return None
    session = provider()
    if session is not None and not session.closed:
        return session
    return None


def bind_shared_session(
        provider: SessionProvider
) -> contextvars.Token[SessionProvider | None]:
    """Bind a session provider as the shared source for the current context.

    Args:
        provider (SessionProvider): a zero-arg callable returning the session
            client calls should reuse (e.g. PooledSession.get).

    Returns:
        contextvars.Token: pass to reset_shared_session to unbind.
    """
    return _shared.set(provider)


def reset_shared_session(
        token: contextvars.Token[SessionProvider | None]) -> None:
    """Unbind the shared session provider using bind_shared_session's token.

    Args:
        token (contextvars.Token): the token returned by bind_shared_session.
    """
    _shared.reset(token)


@asynccontextmanager
async def shared_http_session(
    limit: int = DEFAULT_CONNECTION_LIMIT,
    keepalive_timeout: float = DEFAULT_KEEPALIVE_TIMEOUT,
    ttl_dns_cache: int = DEFAULT_TTL_DNS_CACHE,
) -> AsyncIterator[aiohttp.ClientSession]:
    """Own a pooled session for the duration of the block.

    Binds a keep-alive session so client calls reuse it, and closes it on
    exit. Enter this inside the loop that runs the calls.

    Args:
        limit (int): max simultaneous connections in the pool.
        keepalive_timeout (float): seconds an idle connection is kept alive.
        ttl_dns_cache (int): seconds a resolved host is cached.

    Yields:
        aiohttp.ClientSession: the pooled session (also bound as shared).
    """
    pooled = PooledSession(limit, keepalive_timeout, ttl_dns_cache)
    token = bind_shared_session(pooled.get)
    try:
        yield pooled.get()
    finally:
        reset_shared_session(token)
        await pooled.aclose()
