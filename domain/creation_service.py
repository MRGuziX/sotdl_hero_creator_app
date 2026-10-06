"""Creation transitions independent of Flask and session storage."""

from copy import deepcopy
from pathlib import Path

from pydantic import TypeAdapter

from data.creations import CreationRepository
from domain.creation_state import CreationState, CreationStateError
from models.action import Action, AddLanguage, AddProfession, AddSpell, AddTradition, UpdateLanguage
from models.equipment import Armor, Shield, Weapon
from utils.utils import (
    _expand_dynamic_choice_group,
    advance_hero,
    apply_action,
    benefits_for_new_path_pick,
    expand_any_to_choices,
    get_hero,
    get_spells_for_tradition,
    is_duplicate_expert_path,
    finalize_defense,
    load_json,
    randomly_pick_paths,
)


class CreationError(ValueError):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


class CreationService:
    def __init__(self, repository: CreationRepository):
        self.repository = repository

    def mutate(self, owner, state_id, expected_version, operation):
        state = self.repository.get(owner, state_id)
        if state is None:
            raise CreationError("Creation not found", 404)
        if state.state_version != expected_version:
            raise CreationError("Stale state", 409)
        operation(state)
        state.touch()
        _try_expand_current_group(state)
        finalize_defense(state.hero)
        if not self.repository.save(owner, state, expected_version):
            raise CreationError("Stale state", 409)
        return state


def _has_placeholders(group: list) -> bool:
    for action in group:
        if isinstance(action, AddTradition) and action.name in ("any", "religious_tradition"):
            return True
        if isinstance(action, AddSpell) and (
            action.name in ("known_tradition", "any")
            or action.name.startswith("tradition:")
            or action.name.startswith("tradition_rank0:")
        ):
            return True
        if isinstance(action, AddLanguage) and action.name == "any":
            return True
        if isinstance(action, UpdateLanguage) and action.name == "known":
            return True
        if isinstance(action, AddProfession) and action.name == "any":
            return True
    return False


def _try_expand_current_group(state: CreationState) -> None:
    if state.choice_cursor >= len(state.level_choices):
        return
    group = state.level_choices[state.choice_cursor]
    if not _has_placeholders(group):
        return
    expanded = _expand_dynamic_choice_group(state.hero, group, state.enabled_sources)
    if expanded:
        state.level_choices[state.choice_cursor] = expanded
        state.total_choices_in_level = len(state.level_choices)


def _advance_one_level(state: CreationState) -> None:
    """Advance the hero exactly one level via the domain-authoritative
    `advance_hero` (never re-derived in JS), applying the ancestry's and any
    already-chosen path tiers' benefits for the new level. Levels that grant
    no choices of their own are completed automatically so the crossroads
    never stalls waiting on an empty step.
    """
    if not state.pending_choices and state.current_level not in state.completed_steps:
        state.completed_steps = sorted({*state.completed_steps, state.current_level})

    ancestry = state.creation_inputs.get("ancestry")
    paths = state.creation_inputs.setdefault(
        "paths", {"novice": None, "expert": [], "master": None}
    )
    next_level = state.current_level + 1
    state.hero.level = next_level
    next_choices = advance_hero(
        state.hero,
        ancestry,
        None,
        state.current_level,
        next_level,
        is_random=False,
        paths=paths,
    )
    state.hero.level = next_level
    state.current_level = next_level
    state.choice_cursor = 0
    if next_choices:
        state.level_choices = next_choices
        state.total_choices_in_level = len(next_choices)
    else:
        state.level_choices = []
        state.total_choices_in_level = 0
        state.completed_steps = sorted({*state.completed_steps, next_level})
    state.checkpoint("level")


def _apply_selected_choices(
    state: CreationState, selected_choices: list, choice_cursor: int
) -> tuple[bool, dict | str, int]:
    """Commit a choice batch only after all of its selections succeed."""
    working = deepcopy(state)
    result = _apply_selected_choices_in_place(working, selected_choices, choice_cursor)
    if result[0]:
        state.__dict__.update(working.__dict__)
    return result


def _apply_selected_choices_in_place(
    state: CreationState, selected_choices: list, choice_cursor: int
) -> tuple[bool, dict | str, int]:
    """Validate and apply one or more selected actions for the current pending
    choice group(s).

    Returns `(ok, payload_or_error, http_status)`. On success, `payload`
    is `{"status": "need_choices"}` when more groups remain for this level,
    or `{"status": "done"}` once every group in the current batch has been resolved.
    """
    hero = state.hero
    level_choices = state.level_choices
    if choice_cursor != state.choice_cursor:
        return False, "Invalid choice cursor", 400

    parsed_choices = []
    try:
        action_adapter = TypeAdapter(Action)
        for choice in selected_choices:
            parsed_choices.append(action_adapter.validate_python(choice))
    except (TypeError, ValueError):
        return False, "Invalid choice", 400

    if not parsed_choices or state.choice_cursor >= len(level_choices):
        return False, "Invalid choice", 400

    current_cursor = state.choice_cursor
    for action in parsed_choices:
        if current_cursor >= len(level_choices):
            return False, "Too many selections", 400

        allowed = {a.model_dump_json() for a in level_choices[current_cursor]}
        if action.model_dump_json() not in allowed:
            return False, f"Invalid choice at step {current_cursor}", 400

        state.choice_cursor = current_cursor
        state.total_choices_in_level = len(level_choices)
        state.checkpoint("choice")
        apply_action(action, hero, is_random=False)
        state.applied_actions.append((state.current_level, action))

        for idx, opt in enumerate(level_choices[current_cursor]):
            if opt.model_dump_json() == action.model_dump_json():
                state.selections.setdefault(state.current_level, []).append(idx)
                break

        current_cursor += 1

        if (
            isinstance(action, AddSpell)
            and action.name
            not in (
                "any",
                "known_tradition",
            )
            and not action.name.startswith("tradition:")
            and not action.name.startswith("tradition_rank0:")
        ):
            for i in range(current_cursor, len(level_choices)):
                group = level_choices[i]
                if any(isinstance(a, AddSpell) and a.name == action.name for a in group):
                    filtered = [
                        a for a in group if not (isinstance(a, AddSpell) and a.name == action.name)
                    ]
                    level_choices[i] = filtered if filtered else group

        if isinstance(action, AddTradition) and action.name not in ("any", "religious_tradition"):
            rank0 = get_spells_for_tradition(
                action.name, power_level=0, enabled_sources=state.enabled_sources
            )
            known = {s.name for s in hero.spells}
            if [s for s in rank0 if s not in known]:
                has_sztuczki = any(t.name == "Sztuczki" for t in hero.talents)
                num_picks = 2 if has_sztuczki else 1
                for _ in range(num_picks):
                    marker = AddSpell(name=f"tradition_rank0:{action.name}")
                    level_choices.insert(current_cursor, [marker])

            for i in range(current_cursor, len(level_choices)):
                group = level_choices[i]
                if any(isinstance(a, AddTradition) for a in group):
                    filtered = [
                        a
                        for a in group
                        if not (isinstance(a, AddTradition) and a.name == action.name)
                    ]
                    level_choices[i] = filtered if filtered else group

        if current_cursor < len(level_choices) and _has_placeholders(level_choices[current_cursor]):
            expanded = _expand_dynamic_choice_group(
                hero, level_choices[current_cursor], state.enabled_sources
            )
            if expanded:
                level_choices[current_cursor] = expanded

    state.choice_cursor = current_cursor
    state.total_choices_in_level = len(level_choices)
    if state.choice_cursor < len(level_choices):
        return (True, {"status": "need_choices"}, 200)

    return True, {"status": "done"}, 200


def start_creation(data):
    ancestry = data["ancestry"]
    mode = data["mode"]
    if mode == "random":
        level = data["target_level"]
        paths = data["paths"]
        paths.setdefault("novice", None)
        paths.setdefault("master", None)
        for tier in ("novice", "expert", "master"):
            names = paths["expert"] if tier == "expert" else [paths[tier]]
            for name in names:
                file = Path(__file__).resolve().parent.parent / "data_base" / "paths" / tier
                if name and (name == "cleric_religions" or not (file / f"{name}.json").is_file()):
                    raise CreationError("Unknown path")
        paths = randomly_pick_paths(level, paths)
        hero = get_hero(ancestry, is_random=True, level=level, paths=paths)
        state = CreationState(
            hero=hero,
            mode=mode,
            current_level=level,
            creation_inputs={"ancestry": ancestry, "target_level": level, "paths": paths},
            completed_steps=list(range(level + 1)),
            enabled_sources=data["enabled_sources"],
        )
    else:
        result = get_hero(ancestry, is_random=False, level=0)
        hero, choices = result if isinstance(result, tuple) else (result, [])
        state = CreationState(
            hero=hero,
            level_choices=choices,
            total_choices_in_level=len(choices),
            creation_inputs={
                "ancestry": ancestry,
                "paths": {"novice": None, "expert": [], "master": None},
            },
            enabled_sources=data["enabled_sources"],
        )
    state.checkpoint("level")
    _try_expand_current_group(state)
    return state


def apply_choices(state, data, *, level):
    if level != state.current_level:
        raise CreationError("Step is not active", 409)
    cursor = data.get("choice_cursor", state.choice_cursor)
    ok, result, status = _apply_selected_choices(state, data["selections"], cursor)
    if not ok:
        raise CreationError(result, status)
    if result["status"] == "done":
        state.level_choices = []
        state.choice_cursor = 0
        state.total_choices_in_level = 0
        state.completed_steps = sorted({*state.completed_steps, state.current_level})


def advance(state, data):
    if state.pending_choices:
        raise CreationError("Creation has unresolved choices", 409)
    if not state.can_advance:
        raise CreationError("Complete required paths and equipment before advancing", 409)
    _advance_one_level(state)


def pick_path(state, data, *, tier):
    if tier not in ("novice", "expert", "master"):
        raise CreationError("Unsupported path tier")
    if state.pending_choices:
        raise CreationError("Creation has unresolved choices", 409)
    expected = state.awaiting_path_pick()
    if expected is None or (tier != expected and not (expected == "master" and tier == "expert")):
        raise CreationError("No matching path pick is pending", 409)
    path_id = data["path_id"]
    paths = state.creation_inputs["paths"]
    if is_duplicate_expert_path(paths, tier, path_id):
        raise CreationError("That Expert path was already chosen")
    directory = Path(__file__).resolve().parent.parent / "data_base" / "paths" / tier
    if path_id == "cleric_religions" or not (directory / f"{path_id}.json").is_file():
        raise CreationError("Unknown path")
    state.checkpoint("path")
    before = deepcopy(paths)
    if tier == "expert":
        paths["expert"].append(path_id)
        state.hero.expert_path_names = list(paths["expert"])
    elif tier == "novice":
        paths["novice"] = path_id
        state.hero.path_name = path_id
    else:
        paths["master"] = path_id
        state.hero.master_path_name = path_id
    actions, choices = benefits_for_new_path_pick(before, tier, path_id, state.current_level)
    remaining, expanded = expand_any_to_choices(state.hero, actions, choices)
    for action in remaining:
        apply_action(action, state.hero, is_random=False)
    state.choice_cursor = 0
    state.level_choices = expanded
    state.total_choices_in_level = len(expanded)
    if not expanded:
        state.completed_steps = sorted({*state.completed_steps, state.current_level})


def set_equipment(state, data):
    if not state.awaiting_equipment_pick():
        raise CreationError("Equipment selection not available at this level")
    store = load_json("data_base/equipment/equ.json")["store"]
    picks = {}
    for category, model in (("armors", Armor), ("weapons", Weapon), ("shields", Shield)):
        lookup = {item["name"]: item for item in store[category]}
        if any(name not in lookup for name in data[category]):
            raise CreationError(f"Unknown {category}")
        picks[category] = [model(**lookup[name]) for name in data[category]]
    state.checkpoint("equipment")
    for category, items in picks.items():
        setattr(state.hero.equipment, category, items)
    state.equipment_picks = {
        category: [item.model_dump(mode="json") for item in items]
        for category, items in picks.items()
    }
    state.equipment_confirmed_levels = sorted(
        {*state.equipment_confirmed_levels, state.current_level}
    )


def rewind(state, data):
    target = data["target_level"]
    if target > state.current_level:
        raise CreationError("Invalid rewind target")
    try:
        state.restore_checkpoint("level", target)
    except CreationStateError as error:
        raise CreationError(str(error)) from error
    state.invalidated_levels = list(range(target + 1, 11))


def rewind_choice(state, data):
    try:
        state.restore_checkpoint("choice", state.current_level)
    except CreationStateError as error:
        raise CreationError("Cannot rewind further in this level") from error
