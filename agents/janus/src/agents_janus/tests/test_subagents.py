"""Tests for the subagent system."""
import pytest


def test_subagent_spec_frozen():
    from agents_janus.subagents.base import SubagentSpec
    spec = SubagentSpec(
        name="test", description="test desc", model="m", provider="p",
        spec_path=None, skills=(),
        edits_allow=()
    )
    assert spec.name == "test"
    with pytest.raises(AttributeError):
        spec.name = "other"


def test_subagent_spec_gawt_role():
    from agents_janus.subagents.base import SubagentSpec
    spec = SubagentSpec(
        name="test", description="test desc", model="m", provider="p",
        spec_path=None, skills=(),
        edits_allow=(), gawt_role="custom-role"
    )
    assert spec.gawt_role == "custom-role"

    spec_default = SubagentSpec(
        name="test", description="test desc", model="m", provider="p",
        spec_path=None, skills=(),
        edits_allow=()
    )
    assert spec_default.gawt_role == ""


def test_subagent_spec_no_plugins_field():
    from agents_janus.subagents.base import SubagentSpec
    spec = SubagentSpec(
        name="test", description="", model="", provider="",
        spec_path=None, skills=(),
        edits_allow=()
    )
    assert not hasattr(spec, "plugins")


def test_research_subagent_prompt_disables_implementation_protocol():
    from agents_janus.subagents.base import SubagentSpec
    from agents_janus.subagents.builder import build_subagent_prompt

    spec = SubagentSpec(
        name="test", description="research test", model="m", provider="p",
        spec_path=None, skills=(), edits_allow=()
    )
    prompt = build_subagent_prompt(
        spec,
        {"test": spec},
        coordinator_mode="research",
    )
    assert "research coordinator" in prompt
    assert "Do not edit files" in prompt
    assert "Registration (MANDATORY)" not in prompt


def test_registry_find_owner():
    from agents_janus.subagents.registry import Registry
    from agents_janus.subagents.base import SubagentSpec
    specs = {
        "abm": SubagentSpec(name="abm", description="", model="", provider="", spec_path=None,
                            skills=(), edits_allow=("mal-core/src/mal_core/abm/**",)),
    }
    reg = Registry(specs)
    assert reg.find_owner("mal-core/src/mal_core/abm/engine.hpp") == "abm"
    assert reg.find_owner("other/file.py") is None


def test_registry_loads_gawt_role():
    from agents_janus.subagents.registry import Registry
    from agents_janus.subagents.base import SubagentSpec
    specs = {
        "abm": SubagentSpec(name="abm", description="", model="", provider="", spec_path=None,
                            skills=(), edits_allow=(),
                            gawt_role="abm-worker"),
    }
    reg = Registry(specs)
    spec = reg.get("abm")
    assert spec.gawt_role == "abm-worker"
