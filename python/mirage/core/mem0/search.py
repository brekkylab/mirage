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

import math

from mirage.accessor.mem0 import Mem0Accessor
from mirage.core.mem0._client import search_memories
from mirage.utils.score import format_score


def _validate(query: str, top_k: int, threshold: float) -> None:
    if not query:
        raise ValueError("search: query is required")
    if top_k <= 0:
        raise ValueError("search: top-k must be positive")
    if not math.isfinite(threshold) or threshold < 0 or threshold > 1:
        raise ValueError("search: threshold must be in [0, 1]")


async def search_memories_rendered(
    accessor: Mem0Accessor,
    query: str,
    *,
    mount_prefix: str,
    top_k: int,
    threshold: float,
    memory_ids: set[str] | None = None,
) -> bytes:
    """Run a semantic search in the scope and render ranked results.

    Args:
        accessor (Mem0Accessor): mem0 accessor.
        query (str): search query.
        mount_prefix (str): mount prefix for rendered paths.
        top_k (int): number of results.
        threshold (float): minimum similarity score.
        memory_ids (set[str] | None): optional result id allowlist.
    """
    _validate(query, top_k, threshold)
    results = await search_memories(
        accessor.client,
        query,
        accessor.config.scope_filter,
        top_k=top_k,
        threshold=threshold,
    )
    lines: list[str] = []
    for r in results:
        memory_id = str(r["id"])
        if memory_ids is not None and memory_id not in memory_ids:
            continue
        path = f"{mount_prefix.rstrip('/')}/{memory_id}.json"
        score = format_score(r.get("score"))
        header = path if score is None else f"{path}:{score}"
        lines.append(f"{header}\n{r.get('memory', '')}")
    if not lines:
        return b""
    return ("\n".join(lines) + "\n").encode()
