import json
import logging
import os
import random
import tempfile
import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, send_file, send_from_directory, session, url_for

from models.action import Action
from models.base_hero import AncestryHero
from domain.creation_state import CreationState
from utils.pdf_creator import fill_pdf
from utils.utils import (
    apply_action,
    get_spells_for_tradition,
    get_tradition_name_from_talent,
    get_hero,
    _load_json,
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
_MANUAL_CREATIONS = {}
_MANUAL_CREATION_TTL = 3600
_MAX_MANUAL_CREATIONS = 1000


def _session_id() -> str:
    """Return the stable identifier used to isolate this browser session."""
    if "creation_id" not in session:
        session["creation_id"] = uuid.uuid4().hex
    return session["creation_id"]


def _output_path() -> str:
    """Return the temporary PDF path assigned to the current session."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return str(OUTPUT_DIR / f"{_session_id()}.pdf")


def load_novice_paths() -> list[dict[str, str]]:
    """Load available novice paths from the bundled JSON definitions."""
    paths = []
    for path_file in sorted(NOVICE_PATHS_DIR.glob("*.json")):
        if path_file.name == "cleric_religions.json":
            continue
        path_data = _load_json(str(path_file))
        if "path_name" in path_data and "level_benefits" in path_data:
            paths.append({"id": path_file.stem, "name": path_data["path_name"]})
    return paths


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
                    available_traditions = sorted(
                        set(religions[hero.religion]) - set(traditions)
                    )
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


@app.route("/")
def index():
    descriptions = load_ancestry_descriptions()
    return render_template(
        "index.html",
        ancestry_descriptions=descriptions,
        novice_paths=load_novice_paths(),
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
        result = get_hero(
            ancestry, is_random=is_random, level=level, path_name=path_name
        )

        if isinstance(result, tuple):
            hero, choices = result
            _store_manual_creation(CreationState(hero=hero, pending_choices=choices))
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

    return send_file(
        _output_path(),
        as_attachment=download,
        download_name=f"{ancestry}_hero.pdf",
        mimetype="application/pdf",
    )


@app.route("/confirm_choices", methods=["POST"])
def confirm_choices():
    data = request.get_json(silent=True) or {}
    selected_choices = data.get("selected_choices")
    choice_cursor = data.get("choice_cursor", 0)

    if (
        not selected_choices
        or not isinstance(choice_cursor, int)
        or choice_cursor < 0
    ):
        return "Missing data", 400

    creation = _get_manual_creation()
    if creation is None:
        return "No active creation", 400
    state = creation
    hero = state.hero
    pending_choices = state.pending_choices
    if choice_cursor != state.choice_cursor:
        return "Invalid choice cursor", 400

    parsed_choices = []
    try:
        from pydantic import TypeAdapter

        action_adapter = TypeAdapter(Action)
        for choice in selected_choices:
            parsed_choices.append(action_adapter.validate_python(choice))
    except (TypeError, ValueError):
        return "Invalid choice", 400

    if len(parsed_choices) != 1 or not pending_choices:
        return "Invalid choice", 400
    allowed = {action.model_dump_json() for action in pending_choices[0]}
    if parsed_choices[0].model_dump_json() not in allowed:
        return "Invalid choice", 400
    for action in parsed_choices:
        apply_action(action, hero, is_random=False)
        state.applied_actions.append(action)

    # Re-expand only pending groups against the already-mutated hero. This
    # preserves dynamic religion/tradition behavior without rebuilding rolls.
    from utils.utils import expand_any_to_choices

    _, remaining_choices = expand_any_to_choices(hero, [], pending_choices[1:])
    next_cursor = choice_cursor + 1
    filtered_choices = remaining_choices

    if filtered_choices:
        state.pending_choices = filtered_choices
        state.choice_cursor = next_cursor
        _store_manual_creation(state)
        return jsonify(
            {
                "status": "need_choices",
                "hero_data": hero.model_dump(),
                **choices_response(hero, filtered_choices, next_cursor),
            }
        )

    _MANUAL_CREATIONS.pop(_session_id(), None)
    fill_pdf(hero, _output_path())
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
    """Remove expired pending creations and enforce a bounded process cache."""
    now = time.monotonic()
    expired = [
        key for key, value in _MANUAL_CREATIONS.items()
        if now - value[1] > _MANUAL_CREATION_TTL
    ]
    for key in expired:
        _MANUAL_CREATIONS.pop(key, None)
    while len(_MANUAL_CREATIONS) > _MAX_MANUAL_CREATIONS:
        oldest = min(_MANUAL_CREATIONS, key=lambda key: _MANUAL_CREATIONS[key][1])
        _MANUAL_CREATIONS.pop(oldest, None)


def _store_manual_creation(state: CreationState) -> None:
    """Store pending manual state with a timestamp for bounded cleanup."""
    _purge_manual_creations()
    _MANUAL_CREATIONS[_session_id()] = (state, time.monotonic())


def _get_manual_creation():
    """Return the current pending creation, or `None` when it is absent/expired."""
    _purge_manual_creations()
    creation = _MANUAL_CREATIONS.get(session.get("creation_id"))
    if creation is None:
        return None
    return creation[0]


if __name__ == "__main__":
    app.run(debug=True)
