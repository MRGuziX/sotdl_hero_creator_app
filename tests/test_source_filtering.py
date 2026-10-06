import random

import pytest

from models.action import AddTradition
from utils.utils import _expand_dynamic_choice_group, randomly_pick_paths


def test_pg_tradition_choices_exclude_swd(hero):
    options = _expand_dynamic_choice_group(hero, [AddTradition(name="any")], ["PG"])
    assert options
    assert all("SWD" not in action.name for action in options)


def test_swd_tradition_is_available_when_enabled(hero):
    options = _expand_dynamic_choice_group(hero, [AddTradition(name="any")], ["PG", "SWD"])
    assert any(action.name == "Tradycja Testowa SWD" for action in options)


@pytest.mark.parametrize("seed", range(30))
def test_automatic_pg_paths_exclude_supplement_content(seed):
    random.seed(seed)
    paths = randomly_pick_paths(10, {}, ["PG"])
    assert "swd" not in str(paths)


@pytest.mark.parametrize("extra", [
    {"ancestry": "swd_elf"},
    {"paths": {"expert": ["swd_test"]}},
    {"paths": {"master": "swd_test_master"}},
])
def test_server_rejects_disabled_source_selections(client, extra):
    response = client.post("/api/creations", json={
        "mode": "random", "ancestry": "human", "target_level": 10,
        "enabled_sources": ["PG"], **extra,
    })
    assert response.status_code == 400
    assert "source is not enabled" in response.get_json()["error"]


def test_random_pg_character_contains_no_swd_paths_or_spells(client):
    random.seed(116)
    response = client.post("/api/creations", json={
        "mode": "random", "ancestry": "human", "target_level": 10,
        "enabled_sources": ["PG"],
    })
    assert response.status_code == 200
    state = response.get_json()["state"]
    assert "swd" not in str(state["paths"])
    assert all((spell.get("origin") or {}).get("source", "PG") == "PG"
               for spell in state["hero"]["spells"])
