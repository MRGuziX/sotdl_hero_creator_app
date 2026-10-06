import pytest

from domain.creation_service import CreationError, set_equipment
from domain.creation_state import CreationState


def ready_state(hero):
    return CreationState(
        hero,
        current_level=3,
        creation_inputs={"paths": {"novice": "warrior", "expert": ["fighter"]}},
    )


def test_same_named_weapon_variants_are_selected_by_identity(hero):
    state = ready_state(hero)
    set_equipment(state, {"armors": [], "weapons": ["spear_melee", "spear_thrown"], "shields": []})
    melee, thrown = state.hero.equipment.weapons
    assert melee.name == thrown.name == "Włócznia"
    assert melee.id != thrown.id
    assert "miotana" not in melee.properties
    assert "miotana" in thrown.properties


@pytest.mark.parametrize("picks", [["Włócznia"], ["spear_melee", "spear_melee"]])
def test_ambiguous_or_duplicate_weapon_picks_do_not_mutate(hero, picks):
    state = ready_state(hero)
    before = state.to_dict()
    with pytest.raises(CreationError):
        set_equipment(state, {"armors": [], "weapons": picks, "shields": []})
    assert state.to_dict() == before
