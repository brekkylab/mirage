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

import json
from typing import Any

from mirage.accessor.mem0 import Mem0Accessor
from mirage.cache.index import NULL_INDEX, IndexCacheStore, IndexEntry
from mirage.core.mem0._client import get_all_memories
from mirage.core.mem0.scope import ScopeLevel, detect
from mirage.types import PathSpec
from mirage.utils.errors import enoent, enotdir


def _json_bytes(data: dict[str, Any]) -> bytes:
    return json.dumps(data, ensure_ascii=False, indent=2).encode()


async def readdir(
    accessor: Mem0Accessor,
    path: PathSpec,
    index: IndexCacheStore = NULL_INDEX,
) -> list[str]:
    """List the memory files for the configured scope.

    Args:
        accessor (Mem0Accessor): mem0 accessor.
        path (PathSpec): the directory path (only the mount root is a dir).
        index (IndexCacheStore): index cache.
    """
    scope = detect(path)
    if scope.level == ScopeLevel.INVALID:
        raise enoent(path)
    if scope.level != ScopeLevel.ROOT:
        raise enotdir(path)

    dir_key = path.virtual
    listing = await index.list_dir(dir_key)
    if listing.entries is not None:
        return listing.entries

    memories = await get_all_memories(
        accessor.client,
        filters=accessor.config.scope_filter,
        page_size=accessor.config.default_page_size,
    )
    entries: list[tuple[str, IndexEntry]] = []
    names: list[str] = []
    for m in memories:
        body = _json_bytes(m)
        memory_id = str(m["id"])
        filename = f"{memory_id}.json"
        entry = IndexEntry(
            id=memory_id,
            name=filename,
            resource_type="mem0/memory",
            vfs_name=filename,
            size=len(body),
            remote_time=m.get("updated_at") or m.get("created_at") or "",
            extra={"memory": m},
        )
        entries.append((filename, entry))
        names.append(f"{dir_key.rstrip('/')}/{filename}")
    await index.set_dir(dir_key, entries)
    return names
