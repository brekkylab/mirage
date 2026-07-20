import pytest

from mirage.core.mem0._client import (get_all_memories, get_memory,
                                      search_memories)


class FakeClient:

    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    async def get_all(self, options=None):
        self.calls.append(options.model_dump(exclude_unset=True))
        page = options.page or 1
        return self.pages[page - 1]

    async def get(self, memory_id):
        return {"id": memory_id, "memory": "hi"}

    async def search(self, query, options=None):
        self.calls.append({
            "query": query,
            **options.model_dump(exclude_unset=True)
        })
        return {"results": [{"id": "1", "memory": "m", "score": 0.9}]}


@pytest.mark.asyncio
async def test_get_all_paginates():
    pages = [
        {
            "count": 3,
            "next": "x",
            "results": [{
                "id": "a"
            }, {
                "id": "b"
            }]
        },
        {
            "count": 3,
            "next": None,
            "results": [{
                "id": "c"
            }]
        },
    ]
    client = FakeClient(pages)
    out = await get_all_memories(client, {"user_id": "alex"}, page_size=2)
    assert [m["id"] for m in out] == ["a", "b", "c"]
    assert client.calls[0]["filters"] == {"user_id": "alex"}
    assert client.calls[0]["page"] == 1
    assert client.calls[1]["page"] == 2


@pytest.mark.asyncio
async def test_get_memory():
    client = FakeClient([])
    assert await get_memory(client, "xyz") == {"id": "xyz", "memory": "hi"}


@pytest.mark.asyncio
async def test_search():
    client = FakeClient([])
    out = await search_memories(client,
                                "morning", {"agent_id": "a"},
                                top_k=5,
                                threshold=0.0)
    assert out[0]["score"] == 0.9
    assert client.calls[0]["query"] == "morning"
    assert client.calls[0]["filters"] == {"agent_id": "a"}
    assert client.calls[0]["top_k"] == 5
