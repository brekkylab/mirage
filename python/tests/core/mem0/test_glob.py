import pytest
from pydantic import SecretStr

from mirage.accessor.mem0 import Mem0Accessor
from mirage.cache.index import RAMIndexCacheStore
from mirage.commands.builtin.mem0.io import resolve_glob
from mirage.resource.mem0.config import Mem0Config
from mirage.types import PathSpec


class FakeClient:

    async def get_all(self, options=None):
        return {
            "count": 2,
            "next": None,
            "results": [{
                "id": "aaa",
                "memory": "x"
            }, {
                "id": "bbb",
                "memory": "y"
            }]
        }


def _accessor():
    cfg = Mem0Config(api_key=SecretStr("k"), user_id="alex")
    acc = Mem0Accessor(cfg)
    acc._client = FakeClient()
    return acc


@pytest.mark.asyncio
async def test_passthrough_non_pattern():
    acc = _accessor()
    p = PathSpec(virtual="/mem/aaa.json",
                 directory="/mem",
                 resource_path="aaa.json",
                 resolved=True)
    out = await resolve_glob(acc, [p], RAMIndexCacheStore())
    assert out == [p]


@pytest.mark.asyncio
async def test_expands_star():
    acc = _accessor()
    p = PathSpec(virtual="/mem/*.json",
                 directory="/mem",
                 resource_path="*.json",
                 pattern="*.json",
                 resolved=False)
    out = await resolve_glob(acc, [p], RAMIndexCacheStore())
    assert sorted(x.virtual for x in out) == ["/mem/aaa.json", "/mem/bbb.json"]
