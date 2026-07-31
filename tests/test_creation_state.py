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
        level_choices=[[action]],
        total_choices_in_level=1,
        choice_cursor=2,
        creation_inputs={"ancestry": "human", "level": 0},
        applied_actions=[(0, action)],
    )

    restored = CreationState.from_dict(state.to_dict())

    assert restored.state_id == state.state_id
    assert restored.choice_cursor == 2
    assert restored.level_choices[0][0] == action
    assert restored.applied_actions == [(0, action)]


def test_creation_state_rejects_wrong_version_and_cursor():
    state_data = CreationState(hero=_hero()).to_dict()
    state_data["version"] = 999
    with pytest.raises(CreationStateError, match="version"):
        CreationState.from_dict(state_data)

    state = CreationState(hero=_hero(), choice_cursor=1)
    with pytest.raises(CreationStateError, match="cursor"):
        state.validate_cursor(0)


def test_required_complete_reflects_pending_choices():
    action = AddAttribute(name="strength", value=1)
    state = CreationState(hero=_hero(), level_choices=[[action]], total_choices_in_level=1)

    assert state.required_complete is False
    assert state.public_dict()["required_complete"] is False

    state.choice_cursor = 1
    assert state.required_complete is True
    assert state.public_dict()["required_complete"] is True


def test_can_finalize_is_available_at_any_level_once_choices_are_resolved():
    # Finalize/preview is no longer gated behind reaching level 10: it is
    # always available once a hero exists and has no pending choices.
    state = CreationState(hero=_hero(), current_level=3)

    assert state.can_finalize is True
    assert state.public_dict()["can_finalize"] is True

    state.level_choices = [[AddAttribute(name="strength", value=1)]]
    state.total_choices_in_level = 1
    assert state.can_finalize is False


def test_can_advance_requires_no_pending_choices_and_level_below_ten():
    state = CreationState(hero=_hero(), current_level=9)

    assert state.can_advance is True
    assert state.public_dict()["can_advance"] is True

    state.current_level = 10
    assert state.can_advance is False

    state.current_level = 5
    state.level_choices = [[AddAttribute(name="strength", value=1)]]
    state.total_choices_in_level = 1
    assert state.can_advance is False


def test_awaiting_path_pick_flags_novice_expert_and_master_thresholds():
    state = CreationState(
        hero=_hero(),
        current_level=0,
        creation_inputs={"paths": {"novice": None, "expert": [], "master": None}},
    )
    assert state.awaiting_path_pick() is None  # not level 1 yet

    state.current_level = 1
    assert state.awaiting_path_pick() == "novice"

    state.creation_inputs["paths"]["novice"] = "warrior"
    assert state.awaiting_path_pick() is None

    state.current_level = 3
    assert state.awaiting_path_pick() == "expert"

    state.creation_inputs["paths"]["expert"] = ["fighter"]
    assert state.awaiting_path_pick() is None

    state.current_level = 7
    assert state.awaiting_path_pick() == "master"

    state.creation_inputs["paths"]["master"] = "duelist"
    assert state.awaiting_path_pick() is None

    # A second Expert path instead of Master also satisfies the level 7 pick.
    state.creation_inputs["paths"]["master"] = None
    state.creation_inputs["paths"]["expert"] = ["fighter", "assassin"]
    assert state.awaiting_path_pick() is None

    # Pending choices always suppress the path-pick prompt.
    state.level_choices = [[AddAttribute(name="strength", value=1)]]
    state.total_choices_in_level = 1
    state.choice_cursor = 0
    assert state.awaiting_path_pick() is None