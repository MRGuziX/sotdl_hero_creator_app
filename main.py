import json
import logging
import os
import random
import re
import tempfile
import threading
import time
import uuid
from pathlib import Path

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)
from pydantic import TypeAdapter

from domain.creation_state import CreationState
from models.action import (
    Action,
    AddLanguage,
    AddProfession,
    AddSpell,
    AddTradition,
    UpdateLanguage,
)
from models.base_hero import AncestryHero
from utils.pdf_creator import fill_pdf
from utils.utils import (
    _expand_dynamic_choice_group,
    advance_hero,
    apply_action,
    benefits_for_new_path_pick,
    expand_any_to_choices,
    get_hero,
    get_spells_for_tradition,
    get_tradition_name_from_talent,
    is_duplicate_expert_path,
    randomly_pick_paths,
)
from utils.utils import (
    load_json as _load_json,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)

app = Flask(__name__, static_folder="pictures", static_url_path="/static")
app.secret_key = os.environ.get("SECRET_KEY", "development-only-secret")


@app.route("/assets/<path:filename>")
def assets(filename):
    """Serve extracted presentation assets without changing legacy image URLs."""
    return send_from_directory(PROJECT_ROOT / "static", filename)


ANCESTRIES = ["human", "automaton", "goblin", "dwarf", "orc", "changeling"]

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = Path(tempfile.gettempdir()) / "sotdl_hero_creator"
# Kept for compatibility with callers that import this constant.
OUTPUT_PATH = str(OUTPUT_DIR / "hero_card.pdf")
DESCRIPTIONS_PATH = PROJECT_ROOT / "data_base" / "ancestry" / "descriptions.json"
NOVICE_PATHS_DIR = PROJECT_ROOT / "data_base" / "paths" / "novice"
EXPERT_PATHS_DIR = PROJECT_ROOT / "data_base" / "paths" / "expert"
MASTER_PATHS_DIR = PROJECT_ROOT / "data_base" / "paths" / "master"
PATH_TIERS = ("novice", "expert", "master")
_MANUAL_CREATIONS = {}
_MANUAL_CREATIONS_LOCK = threading.Lock()
_MANUAL_CREATION_TTL = 3600
_MAX_MANUAL_CREATIONS = 1000
_SAFE_PATH_ID = re.compile(r"^[a-z0-9_]+$")


def _session_id() -> str:
    """Return the stable identifier used to isolate this browser session."""
    if "creation_id" not in session:
        session["creation_id"] = uuid.uuid4().hex
    return session["creation_id"]


def _output_path() -> str:
    """Return the temporary PDF path assigned to the current session."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return str(OUTPUT_DIR / f"{_session_id()}.pdf")


def _load_paths(directory: Path, *, skip: set[str] | None = None) -> list[dict[str, str]]:
    paths = []
    for path_file in sorted(directory.glob("*.json")):
        if skip and path_file.name in skip:
            continue
        path_data = _load_json(str(path_file))
        if "path_name" in path_data and "level_benefits" in path_data:
            paths.append({"id": path_file.stem, "name": path_data["path_name"]})
    return paths


def load_novice_paths() -> list[dict[str, str]]:
    return _load_paths(NOVICE_PATHS_DIR, skip={"cleric_religions.json"})


def load_expert_paths() -> list[dict[str, str]]:
    return _load_paths(EXPERT_PATHS_DIR)


def load_master_paths() -> list[dict[str, str]]:
    return _load_paths(MASTER_PATHS_DIR)


def _path_file_exists(tier: str, path_id: str) -> bool:
    """Return whether a path definition file exists for `tier`/`path_id`."""
    return (PROJECT_ROOT / "data_base" / "paths" / tier / f"{path_id.lower()}.json").exists()


def _normalize_paths_input(raw: dict | None) -> dict:
    """Normalize a client-supplied path selection into the canonical
    `{"novice": ..., "expert": [...], "master": ...}` shape used throughout
    the creation contract."""
    raw = raw or {}
    return {
        "novice": raw.get("novice") or None,
        "expert": [name for name in (raw.get("expert") or []) if name],
        "master": raw.get("master") or None,
    }


def choice_context(hero: AncestryHero, choices: list[list[Action]]) -> dict:
    """Return the lists needed to make tradition and spell choices explicit."""
    traditions = sorted(
        {
            get_tradition_name_from_talent(t.name)
            for t in hero.talents
            if get_tradition_name_from_talent(t.name)
        }
    )
    spells_by_tradition = {
        tradition: sorted(
            set(get_spells_for_tradition(tradition, hero.power))
            - {spell.name for spell in hero.spells}
        )
        for tradition in traditions
    }
    available_traditions = []
    for group in choices:
        for action in group:
            if action.type == "add_tradition" and action.name == "religious_tradition":
                religions = _load_json("data_base/paths/novice/cleric_religions.json")
                if hero.religion in religions:
                    available_traditions = sorted(set(religions[hero.religion]) - set(traditions))
            elif action.type == "add_spell" and action.name == "known_tradition":
                break
    return {
        "known_traditions": traditions,
        "available_traditions": available_traditions,
        "spells_by_tradition": spells_by_tradition,
    }


def choices_response(
    hero: AncestryHero, choices: list[list[Action]], choice_cursor: int = 0
) -> dict:
    return {
        "choices": [[a.model_dump() for a in choices[0]]] if choices else [],
        "choice_cursor": choice_cursor,
        **choice_context(hero, choices[:1]),
    }


def load_ancestry_descriptions() -> dict:
    with open(DESCRIPTIONS_PATH, "r", encoding="utf-8") as descriptions_file:
        return json.load(descriptions_file)


def rebuild_hero(state: CreationState):
    """Rebuild the hero from scratch up to the current level and cursor."""
    ancestry = state.creation_inputs["ancestry"]
    paths = state.creation_inputs.get("paths", {})

    # 1. Start with the level 0 baseline
    hero = get_hero(ancestry, is_random=False, level=0)
    if isinstance(hero, tuple):
        hero, _ = hero

    # Apply choices for level 0 from applied_actions
    for lvl, action in state.applied_actions:
        if lvl == 0:
            apply_action(action, hero, is_random=False)

    # 2. Advance and apply choices for each level up to current_level
    for lvl in range(1, state.current_level + 1):
        # We need to advance without adding NEW choices to CreationState,
        # but just to get the hero object updated with deterministic benefits.
        # advance_hero normally returns expanded choices which we ignore here
        # because they should already be in state.level_choices or applied_actions.
        advance_hero(hero, ancestry, None, lvl - 1, lvl, is_random=False, paths=paths)
        for action_lvl, action in state.applied_actions:
            if action_lvl == lvl:
                apply_action(action, hero, is_random=False)

    hero.path_name = paths.get("novice")
    hero.expert_path_names = list(paths.get("expert") or [])
    hero.master_path_name = paths.get("master")
    state.hero = hero


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
    expanded = _expand_dynamic_choice_group(state.hero, group)
    if expanded:
        state.level_choices[state.choice_cursor] = expanded
        state.total_choices_in_level = len(state.level_choices)


def _creation_response(state: CreationState, download_url: str | None = None) -> dict:
    """Build the versioned JSON contract used by the component frontend."""
    _try_expand_current_group(state)
    public = state.public_dict()
    total_choices = state.total_choices_in_level
    current_index = min(state.choice_cursor + 1, total_choices) if total_choices else 0
    response = {
        "creation_id": state.state_id,
        "state": public,
        "step": {
            "level": state.current_level,
            "required": not state.required_complete,
            "current_choice_index": current_index,
            "total_choices_in_level": total_choices,
            "can_advance": state.can_advance,
            "can_finalize": state.can_finalize,
            "awaiting_path_pick": state.awaiting_path_pick(),
            "available_choices": public["pending_choices"],
            "selections": public["selections"],
            # Magic/tradition context for the pending step, so the frontend
            # (MagicDashboard/GrimoirePanel groundwork) can render spell and
            # tradition choices with their real names/groupings instead of
            # generic action labels, without duplicating any SotDL rules.
            **choice_context(
                state.hero, state.level_choices[state.choice_cursor : state.choice_cursor + 1]
            ),
        },
    }
    if download_url is not None:
        response["download_url"] = download_url
    return response


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


@app.post("/api/creations")
def api_start_creation():
    """Start a manual or random creation without trusting client hero data."""
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "manual")
    ancestry = data.get("ancestry")
    if mode not in {"manual", "random"} or ancestry not in ANCESTRIES:
        return jsonify({"error": "Unsupported mode or ancestry"}), 400

    if mode == "random":
        # Random mode resolves every choice itself, so there is nothing to
        # gate step-by-step: build straight to the requested level in one
        # shot. Its request/response contract is unchanged by this feature:
        # it still accepts `target_level` alongside the path selection.
        try:
            level = int(data.get("target_level", 0))
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid target level"}), 400
        if not 0 <= level <= 10:
            return jsonify({"error": "Invalid target level"}), 400
        paths = _normalize_paths_input(data.get("paths"))
        paths = randomly_pick_paths(level, paths)
        creation_inputs = {"ancestry": ancestry, "target_level": level, "paths": paths}
        hero = get_hero(ancestry, is_random=True, level=level, paths=paths)
        state = CreationState(
            hero=hero,
            level_choices=[],
            creation_inputs=creation_inputs,
            mode=mode,
            current_level=level,
            completed_steps=list(range(level + 1)),
        )
    else:
        # Manual mode always starts at level 0 with only the ancestry
        # decided; Novice/Expert/Master paths are picked later, exactly when
        # their level_benefits unlock, via `/api/creations/<id>/paths/<tier>`.
        creation_inputs = {
            "ancestry": ancestry,
            "paths": {"novice": None, "expert": [], "master": None},
        }
        result = get_hero(ancestry, is_random=False, level=0)
        hero, choices = result if isinstance(result, tuple) else (result, [])
        state = CreationState(
            hero=hero,
            level_choices=choices,
            creation_inputs=creation_inputs,
            mode=mode,
            current_level=0,
            total_choices_in_level=len(choices),
        )

    _store_manual_creation(state)
    return jsonify(_creation_response(state))


@app.get("/api/creations/<creation_id>")
def api_get_creation(creation_id):
    state = _get_manual_creation()
    if state is None or state.state_id != creation_id:
        return jsonify({"error": "Creation not found"}), 404
    return jsonify(_creation_response(state))


@app.post("/api/creations/<creation_id>/steps/<int:level>/choices")
def api_apply_choices(creation_id, level):
    state = _get_manual_creation()
    data = request.get_json(silent=True) or {}
    if state is None or state.state_id != creation_id:
        return jsonify({"error": "Creation not found"}), 404
    if level != state.current_level:
        return jsonify({"error": "Step is not active"}), 409
    if data.get("state_version") != state.state_version:
        return jsonify({"error": "Stale state"}), 409

    selected_choices = data.get("selections", data.get("selected_choices"))
    choice_cursor = data.get("choice_cursor", state.choice_cursor)
    if not selected_choices or not isinstance(choice_cursor, int) or choice_cursor < 0:
        return jsonify({"error": "Missing data"}), 400

    ok, result, status = _apply_selected_choices(state, selected_choices, choice_cursor)
    if not ok:
        return jsonify({"error": result}), status

    if result["status"] == "need_choices":
        state.touch()
        _store_manual_creation(state)
        return jsonify(_creation_response(state))

    # This level's choice groups were fully consumed. The wizard no longer
    # auto-advances toward a pre-chosen target level: the crossroads screen
    # (`can_advance`/`can_finalize`) lets the player explicitly decide to
    # progress one more level or preview/save the hero right here.
    state.level_choices = []
    state.choice_cursor = 0
    state.total_choices_in_level = 0
    state.completed_steps = sorted({*state.completed_steps, state.current_level})
    state.touch()
    _store_manual_creation(state)
    return jsonify(_creation_response(state))


@app.post("/api/creations/<creation_id>/advance")
def api_advance_creation(creation_id):
    """Advance the wizard exactly one level, replacing the previous
    auto-loop-to-target behavior with an explicit, single-level step that
    the crossroads screen triggers on demand."""
    state = _get_manual_creation()
    data = request.get_json(silent=True) or {}
    if state is None or state.state_id != creation_id:
        return jsonify({"error": "Creation not found"}), 404
    if data.get("state_version") != state.state_version:
        return jsonify({"error": "Stale state"}), 409
    if state.pending_choices:
        return jsonify({"error": "Creation has unresolved choices"}), 409
    if state.current_level >= 10:
        return jsonify({"error": "Hero is already at the maximum level"}), 409

    _advance_one_level(state)
    state.touch()
    _store_manual_creation(state)
    return jsonify(_creation_response(state))


@app.post("/api/creations/<creation_id>/paths/<tier>")
def api_pick_path(creation_id, tier):
    """Record the path chosen for `tier` (novice/expert/master) before its
    level_benefits are resolved, then immediately resolve them for the
    current level, mirroring `advance_hero`'s incremental behavior."""
    state = _get_manual_creation()
    if state is None or state.state_id != creation_id:
        return jsonify({"error": "Creation not found"}), 404
    if tier not in PATH_TIERS:
        return jsonify({"error": "Unsupported path tier"}), 400

    data = request.get_json(silent=True) or {}
    if data.get("state_version") != state.state_version:
        return jsonify({"error": "Stale state"}), 409
    if state.pending_choices:
        return jsonify({"error": "Creation has unresolved choices"}), 409

    path_id = data.get("path_id") or data.get("path")
    if not path_id:
        return jsonify({"error": "Missing path_id"}), 400
    if not _SAFE_PATH_ID.match(path_id.lower()):
        return jsonify({"error": "Invalid path_id"}), 400

    expected_tier = state.awaiting_path_pick()
    # At the level 7 crossroads, `expected_tier` is reported as "master"
    # even though the player may instead pick a second Expert path.
    if expected_tier is None or (
        tier != expected_tier and not (expected_tier == "master" and tier == "expert")
    ):
        return jsonify({"error": "No matching path pick is pending"}), 409

    paths = state.creation_inputs.setdefault(
        "paths", {"novice": None, "expert": [], "master": None}
    )
    if is_duplicate_expert_path(paths, tier, path_id):
        return jsonify({"error": "That Expert path was already chosen"}), 400
    if not _path_file_exists(tier, path_id):
        return jsonify({"error": "Unknown path"}), 400

    paths_before = {
        "novice": paths.get("novice"),
        "expert": list(paths.get("expert") or []),
        "master": paths.get("master"),
    }
    if tier == "expert":
        paths["expert"] = [*paths.get("expert", []), path_id]
        state.hero.expert_path_names = list(paths["expert"])
    elif tier == "novice":
        paths["novice"] = path_id
        state.hero.path_name = path_id
    else:
        paths["master"] = path_id
        state.hero.master_path_name = path_id

    actions, choices = benefits_for_new_path_pick(paths_before, tier, path_id, state.current_level)
    remaining_actions, expanded_choices = expand_any_to_choices(state.hero, actions, choices)
    for action in remaining_actions:
        apply_action(action, state.hero, is_random=False)

    state.choice_cursor = 0
    if expanded_choices:
        state.level_choices = expanded_choices
        state.total_choices_in_level = len(expanded_choices)
    else:
        state.level_choices = []
        state.choice_cursor = 0
        state.total_choices_in_level = 0
        state.completed_steps = sorted({*state.completed_steps, state.current_level})

    state.touch()
    _store_manual_creation(state)
    return jsonify(_creation_response(state))


@app.post("/api/creations/<creation_id>/rewind")
def api_rewind_creation(creation_id):
    state = _get_manual_creation()
    data = request.get_json(silent=True) or {}
    if state is None or state.state_id != creation_id:
        return jsonify({"error": "Creation not found"}), 404
    if data.get("state_version") != state.state_version:
        return jsonify({"error": "Stale state"}), 409
    try:
        target = int(data["target_level"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid target level"}), 400
    if target < 0 or target > state.current_level:
        return jsonify({"error": "Invalid rewind target"}), 400

    # Clear path selections that belong to future levels
    paths = state.creation_inputs.get("paths", {})
    if target < 1:
        paths["novice"] = None
    if target < 3:
        paths["expert"] = []
    if target < 7:
        paths["expert"] = paths.get("expert", [])[:1]
        paths["master"] = None

    state.current_level = target
    state.choice_cursor = 0
    state.completed_steps = [step for step in state.completed_steps if step < target]
    state.invalidated_levels = [step for step in range(target + 1, 11)]
    state.applied_actions = [(lvl, act) for lvl, act in state.applied_actions if lvl < target]
    for lvl in list(state.selections.keys()):
        if lvl >= target:
            del state.selections[lvl]

    rebuild_hero(state)

    # Restore level_choices for the target level
    ancestry = state.creation_inputs.get("ancestry")
    if target == 0:
        result = get_hero(ancestry, is_random=False, level=0)
        _, choices = result if isinstance(result, tuple) else (result, [])
        state.level_choices = choices
    else:
        state.level_choices = advance_hero(
            state.hero, ancestry, None, target - 1, target, is_random=False, paths=paths
        )
    state.total_choices_in_level = len(state.level_choices)

    state.touch()
    _store_manual_creation(state)
    return jsonify(
        {
            "state": state.public_dict(),
            "invalidated_steps": state.invalidated_levels,
            **_creation_response(state),
        }
    )


@app.post("/api/creations/<creation_id>/rewind_choice")
def api_rewind_choice(creation_id):
    state = _get_manual_creation()
    if state is None or state.state_id != creation_id:
        return jsonify({"error": "Creation not found"}), 404
    data = request.get_json(silent=True) or {}
    if data.get("state_version") != state.state_version:
        return jsonify({"error": "Stale state"}), 409
    if state.choice_cursor <= 0:
        return jsonify({"error": "Cannot rewind further in this level"}), 400

    saved_selections = list(state.selections.get(state.current_level, []))
    saved_selections.pop()

    state.applied_actions = [
        (lvl, act) for lvl, act in state.applied_actions if lvl != state.current_level
    ]
    state.selections[state.current_level] = []

    actual_level = state.current_level
    state.current_level = max(0, actual_level - 1)
    rebuild_hero(state)
    state.current_level = actual_level

    ancestry = state.creation_inputs.get("ancestry")
    paths = state.creation_inputs.get("paths", {})
    if actual_level == 0:
        result = get_hero(ancestry, is_random=False, level=0)
        _, choices = result if isinstance(result, tuple) else (result, [])
        state.level_choices = choices
    else:
        state.level_choices = advance_hero(
            state.hero,
            ancestry,
            None,
            actual_level - 1,
            actual_level,
            is_random=False,
            paths=paths,
        )

    state.choice_cursor = 0

    for sel_idx in saved_selections:
        group = state.level_choices[state.choice_cursor]
        if _has_placeholders(group):
            group = _expand_dynamic_choice_group(state.hero, group)
            state.level_choices[state.choice_cursor] = group
        action = group[sel_idx]
        _apply_selected_choices(state, [action.model_dump(mode="json")], state.choice_cursor)

    state.total_choices_in_level = len(state.level_choices)
    _try_expand_current_group(state)
    state.touch()
    _store_manual_creation(state)
    return jsonify(_creation_response(state))


@app.post("/api/creations/<creation_id>/finalize")
def api_finalize_creation(creation_id):
    state = _get_manual_creation()
    if state is None or state.state_id != creation_id:
        return jsonify({"error": "Creation not found"}), 404
    if state.pending_choices:
        return jsonify({"error": "Creation has unresolved choices"}), 409
    fill_pdf(state.hero, _output_path())
    return jsonify(
        {"summary": state.hero.model_dump(mode="json"), "pdf_url": url_for("download_current")}
    )


@app.route("/")
def index():
    descriptions = load_ancestry_descriptions()
    return render_template(
        "index.html",
        ancestry_descriptions=descriptions,
        novice_paths=load_novice_paths(),
        expert_paths=load_expert_paths(),
        master_paths=load_master_paths(),
    )


@app.route("/roll/<ancestry>")
def roll(ancestry):
    if ancestry not in ANCESTRIES:
        return "Invalid ancestry", 400

    download = request.args.get("download", "0") == "1"
    is_random = request.args.get("is_random", "1") == "1"
    try:
        level = int(request.args.get("level", "0"))
    except (TypeError, ValueError):
        return "Invalid level", 400
    if level < 0:
        return "Invalid level", 400
    path_name = request.args.get("path")

    if not download:
        result = get_hero(ancestry, is_random=is_random, level=level, path_name=path_name)

        if isinstance(result, tuple):
            hero, choices = result
            _store_manual_creation(
                CreationState(hero=hero, level_choices=choices, total_choices_in_level=len(choices))
            )
            return jsonify(
                {
                    "status": "need_choices",
                    "hero_data": hero.model_dump(),
                    # Manual creation is intentionally a wizard: expose only the
                    # next unresolved choice so later choices see earlier picks.
                    **choices_response(hero, choices),
                }
            )

        hero = result
        fill_pdf(hero, _output_path())
        return jsonify({"status": "success", "download_url": url_for("download_current")})

    return send_file(
        _output_path(),
        as_attachment=download,
        download_name=f"{ancestry}_hero.pdf",
        mimetype="application/pdf",
    )


def _apply_selected_choices(
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
            rank0 = get_spells_for_tradition(action.name, power_level=0)
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
            expanded = _expand_dynamic_choice_group(hero, level_choices[current_cursor])
            if expanded:
                level_choices[current_cursor] = expanded

    state.choice_cursor = current_cursor
    state.total_choices_in_level = len(level_choices)
    if state.choice_cursor < len(level_choices):
        return (True, {"status": "need_choices"}, 200)

    return True, {"status": "done"}, 200


@app.route("/confirm_choices", methods=["POST"])
def confirm_choices():
    data = request.get_json(silent=True) or {}
    selected_choices = data.get("selected_choices", data.get("selections"))
    choice_cursor = data.get("choice_cursor", 0)

    if not selected_choices or not isinstance(choice_cursor, int) or choice_cursor < 0:
        return "Missing data", 400

    state = _get_manual_creation()
    if state is None:
        return "No active creation", 400

    ok, result, status = _apply_selected_choices(state, selected_choices, choice_cursor)
    if not ok:
        return result, status

    if result["status"] == "need_choices":
        state.touch()
        _store_manual_creation(state)
        return jsonify(
            {
                "status": "need_choices",
                "hero_data": state.hero.model_dump(),
                **choices_response(
                    state.hero, state.level_choices[state.choice_cursor :], state.choice_cursor
                ),
            }
        )

    _MANUAL_CREATIONS.pop(_session_id(), None)
    fill_pdf(state.hero, _output_path())
    return jsonify({"status": "success", "download_url": url_for("download_current")})


@app.route("/roll_random")
def roll_random():
    random_ancestry = random.choice(ANCESTRIES)
    return redirect(url_for("roll", ancestry=random_ancestry, **request.args))


@app.route("/download_current")
def download_current():
    output_path = _output_path()
    if not os.path.exists(output_path):
        return "No hero generated yet", 404

    download = request.args.get("download", "0") == "1"

    return send_file(
        output_path,
        as_attachment=download,
        download_name="hero_card.pdf",
        mimetype="application/pdf",
    )


def _purge_manual_creations() -> None:
    """Remove expired pending creations and enforce a bounded process cache.

    Must be called while holding ``_MANUAL_CREATIONS_LOCK``.
    """
    now = time.monotonic()
    expired = [
        key for key, value in _MANUAL_CREATIONS.items() if now - value[1] > _MANUAL_CREATION_TTL
    ]
    for key in expired:
        _MANUAL_CREATIONS.pop(key, None)
    while len(_MANUAL_CREATIONS) > _MAX_MANUAL_CREATIONS:
        oldest = min(_MANUAL_CREATIONS, key=lambda key: _MANUAL_CREATIONS[key][1])
        _MANUAL_CREATIONS.pop(oldest, None)


def _store_manual_creation(state: CreationState) -> None:
    """Store pending manual state with a timestamp for bounded cleanup."""
    with _MANUAL_CREATIONS_LOCK:
        _purge_manual_creations()
        _MANUAL_CREATIONS[_session_id()] = (state, time.monotonic())


def _get_manual_creation():
    """Return the current pending creation, or `None` when it is absent/expired."""
    with _MANUAL_CREATIONS_LOCK:
        _purge_manual_creations()
        creation = _MANUAL_CREATIONS.get(session.get("creation_id"))
    if creation is None:
        return None
    return creation[0]


if __name__ == "__main__":
    app.run(debug=True)
