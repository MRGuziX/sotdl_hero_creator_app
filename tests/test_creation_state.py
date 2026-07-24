import pytest

from data.repository import DataRepositoryError, load_ancestry, load_novice_path
from domain.creation_state import CreationState, CreationStateError
from models.action import AddAttribute
from models.base_hero import AncestryHero


def _hero():
    return AncestryHero(
        ancestry_name="Człowiek",
        ancestry_id="human",
        strength=10,
        dexterity=10,
        intelligence=10,
        will=10,
        perception=10,
        defense=10,
        health=10,
        healing_rate=1,
        size=[1.0, 1.0],
        speed=10,
    )


def test_repository_validates_existing_data():
    assert load_ancestry("human").general.ancestry_name
    assert load_novice_path("mage").path_name


def test_repository_reports_missing_data_clearly():
    with pytest.raises(DataRepositoryError, match="not found"):
        load_ancestry("does-not-exist")


def test_creation_state_round_trips_hero_actions_and_cursor():
    action = AddAttribute(name="strength", value=1)
    state = CreationState(
        hero=_hero(),
        pending_choices=[[action]],
        choice_cursor=2,
        creation_inputs={"ancestry": "human", "level": 0},
        applied_actions=[action],
        roll_results={"past": 7},
    )

    restored = CreationState.from_dict(state.to_dict())

    assert restored.state_id == state.state_id
    assert restored.choice_cursor == 2
    assert restored.pending_choices[0][0] == action
    assert restored.applied_actions == [action]
    assert restored.roll_results == {"past": 7}


def test_creation_state_rejects_wrong_version_and_cursor():
    state_data = CreationState(hero=_hero()).to_dict()
    state_data["version"] = 999
    with pytest.raises(CreationStateError, match="version"):
        CreationState.from_dict(state_data)

    state = CreationState(hero=_hero(), choice_cursor=1)
    with pytest.raises(CreationStateError, match="cursor"):
        state.validate_cursor(0)