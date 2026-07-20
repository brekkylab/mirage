from pydantic import SecretStr

from mirage.resource.mem0 import Mem0Config
from mirage.resource.mem0.mem0 import Mem0Resource
from mirage.types import ResourceName


def test_resource_basic():
    cfg = Mem0Config(api_key=SecretStr("secret"), user_id="alex")
    res = Mem0Resource(cfg)
    assert res.name == ResourceName.MEM0
    assert res.caches_reads is True
    assert res.SUPPORTS_SNAPSHOT is False


def test_get_state_redacts_api_key():
    cfg = Mem0Config(api_key=SecretStr("secret"), user_id="alex")
    res = Mem0Resource(cfg)
    state = res.get_state()
    assert state["type"] == ResourceName.MEM0
    assert "secret" not in str(state)


def test_resource_uses_generic_read_only_surface():
    cfg = Mem0Config(api_key=SecretStr("secret"), user_id="alex")
    res = Mem0Resource(cfg)
    commands = {command.name for command in res.commands()}
    assert {"cat", "find", "grep", "jq", "ls", "rg", "search",
            "stat"} <= commands
    assert {op.name for op in res.ops_list()} == {"read", "readdir", "stat"}
