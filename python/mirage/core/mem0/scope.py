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

from dataclasses import dataclass
from enum import StrEnum

from mirage.types import PathSpec


class ScopeLevel(StrEnum):
    ROOT = "root"
    MEMORY = "memory"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class Mem0Scope:
    level: ScopeLevel
    memory_id: str | None = None


def _backend_key(path: PathSpec) -> str:
    return path.resource_path.strip("/")


def detect(path: PathSpec) -> Mem0Scope:
    """Classify a mem0 virtual path.

    Args:
        path (PathSpec): the virtual path to classify.
    """
    key = _backend_key(path)
    if not key:
        return Mem0Scope(level=ScopeLevel.ROOT)
    parts = key.split("/")
    if any(p.startswith(".") for p in parts):
        return Mem0Scope(level=ScopeLevel.INVALID)
    if len(parts) == 1 and len(
            parts[0]) > len(".json") and parts[0].endswith(".json"):
        return Mem0Scope(level=ScopeLevel.MEMORY,
                         memory_id=parts[0][:-len(".json")])
    return Mem0Scope(level=ScopeLevel.INVALID)
