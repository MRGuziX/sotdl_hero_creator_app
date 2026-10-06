import random

import pytest

from models.action import AddSpell, AddTradition
from utils.utils import (
    _expand_dynamic_choice_group,
    add_profession,
    add_tradition,
    expand_any_to_choices,
    get_hero,
    resolve_choices,
)


def test_infiltrator_profession_uses_an_existing_category(hero):
    add_profession("przestępcza", hero)
    assert hero.professions


def test_future_spell_alternative_survives_until_tradition_is_known(hero):
    hero.power = 1
    definition = [
        AddTradition(name="Tradycja Powietrza"),
        AddSpell(name="tradition:Tradycja Powietrza"),
    ]
    _, groups = expand_any_to_choices(hero, [], [definition], defer_dynamic=True)
    add_tradition("Tradycja Powietrza", hero)
    available = _expand_dynamic_choice_group(hero, groups[0])
    assert available
    assert all(isinstance(action, AddSpell) for action in available)


def test_exhausted_choice_never_selects_from_an_empty_group(hero):
    add_tradition("Tradycja Powietrza", hero)
    assert resolve_choices(hero, [], [[AddTradition(name="Tradycja Powietrza")]]) == []


@pytest.mark.parametrize("seed", [2, 116])
def test_previously_crashing_random_api_generations_complete(client, seed):
    random.seed(seed)
    response = client.post(
        "/api/creations", json={"mode": "random", "ancestry": "goblin", "target_level": 10}
    )
    assert response.status_code == 200
    assert response.get_json()["state"]["hero"]["level"] == 10


@pytest.mark.parametrize("seed", range(40))
def test_random_progression_sample(seed):
    random.seed(seed)
    ancestry = ("human", "automaton", "goblin", "dwarf", "orc", "changeling")[seed % 6]
    hero = get_hero(ancestry, True, level=10)
    assert hero.level == 10
    assert len({spell.name for spell in hero.spells}) == len(hero.spells)
    assert all(spell.name not in {"any", "known_tradition"} for spell in hero.spells)
