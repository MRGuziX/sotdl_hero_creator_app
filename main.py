import json
import logging
import os
import re
import tempfile
import uuid
from pathlib import Path

from flask import (
    Flask,
    abort,
    jsonify,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)
from pydantic import ValidationError

from config import secret_key
from data.creations import MemoryCreationRepository
from domain import creation_service as commands
from domain.creation_service import CreationError, CreationService, _try_expand_current_group

from domain.creation_state import CreationState
from models.action import (
    Action,
)
from models.base_hero import AncestryHero
from models.requests import (
    ApplyChoices,
    PickEquipment,
    PickPath,
    Rewind,
    StartCreation,
    VersionedRequest,
)
from utils.pdf_creator import fill_pdf
from utils.utils import (
    finalize_defense,
    get_spell_descriptions,
    get_spells_for_tradition,
    get_tradition_name_from_talent,
    load_json as _load_json,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)

app = Flask(__name__, static_folder="pictures", static_url_path="/static")
app.secret_key = secret_key(development=__name__ == "__main__")


@app.route("/assets/<path:filename>")
def assets(filename):
    """Serve extracted presentation assets without changing legacy image URLs."""
    return send_from_directory(PROJECT_ROOT / "static", filename)


ANCESTRIES = ["human", "automaton", "goblin", "dwarf", "orc", "changeling", "swd_elf"]

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = Path(tempfile.gettempdir()) / "sotdl_hero_creator"
# Kept for compatibility with callers that import this constant.
OUTPUT_PATH = str(OUTPUT_DIR / "hero_card.pdf")
DESCRIPTIONS_PATH = PROJECT_ROOT / "data_base" / "ancestry" / "descriptions.json"
NOVICE_PATHS_DIR = PROJECT_ROOT / "data_base" / "paths" / "novice"
EXPERT_PATHS_DIR = PROJECT_ROOT / "data_base" / "paths" / "expert"
MASTER_PATHS_DIR = PROJECT_ROOT / "data_base" / "paths" / "master"
PATH_TIERS = ("novice", "expert", "master")
app.config["CREATION_REPOSITORY"] = MemoryCreationRepository()
_SAFE_SESSION_ID = re.compile(r"[a-f0-9]{32}")


class RequestValidationError(ValueError):
    pass


@app.errorhandler(RequestValidationError)
def invalid_api_request(error):
    return jsonify({"error": str(error)}), 400


def _request_data(model) -> dict:
    raw = request.get_json(silent=True)
    if raw is None and not request.get_data():
        raw = {}
    if not isinstance(raw, dict):
        raise RequestValidationError("Request body must be a JSON object")
    try:
        return model.model_validate(raw).model_dump(mode="json", exclude_none=True)
    except ValidationError as error:
        field = ".".join(str(part) for part in error.errors()[0]["loc"])
        raise RequestValidationError(f"Invalid {field or 'request'}") from error


def _session_id() -> str:
    """Return the stable identifier used to isolate this browser session."""
    if "creation_id" not in session:
        session["creation_id"] = uuid.uuid4().hex
    identifier = session["creation_id"]
    if not isinstance(identifier, str) or not _SAFE_SESSION_ID.fullmatch(identifier):
        abort(400, description="Invalid session identifier")
    return identifier


def _output_path() -> str:
    """Return the temporary PDF path assigned to the current session."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    root = OUTPUT_DIR.resolve()
    destination = (root / f"{_session_id()}.pdf").resolve()
    if destination.parent != root:
        abort(400, description="Invalid PDF destination")
    return str(destination)


def _load_paths(directory: Path, *, skip: set[str] | None = None) -> list[dict[str, str]]:
    paths = []
    for path_file in sorted(directory.glob("*.json")):
        if skip and path_file.name in skip:
            continue
        path_data = _load_json(str(path_file))
        if "path_name" in path_data and "level_benefits" in path_data:
            origin = path_data.get("origin") or {}
            entry = {
                "id": path_file.stem,
                "name": path_data["path_name"],
                "source": origin.get("source", "PG"),
            }
            if path_data.get("path_description"):
                entry["description"] = path_data["path_description"]
            paths.append(entry)
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


def choice_context(
    hero: AncestryHero,
    choices: list[list[Action]],
    enabled_sources: list[str] | None = None,
) -> dict:
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
            set(get_spells_for_tradition(tradition, hero.power, enabled_sources))
            - {spell.name for spell in hero.spells}
        )
        for tradition in traditions
    }
    spell_descriptions = {}
    for tradition in traditions:
        spell_descriptions.update(get_spell_descriptions(tradition, hero.power, enabled_sources))
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
        "spell_descriptions": spell_descriptions,
    }


_equipment_store_cache = None


def _load_equipment_store() -> dict:
    global _equipment_store_cache
    if _equipment_store_cache is None:
        _equipment_store_cache = _load_json("data_base/equipment/equ.json")["store"]
    return _equipment_store_cache


def load_ancestry_descriptions() -> dict:
    with open(DESCRIPTIONS_PATH, "r", encoding="utf-8") as descriptions_file:
        return json.load(descriptions_file)


def load_ancestry_list() -> list[dict[str, str]]:
    """Build the ancestry list from descriptions.json including source info."""
    descriptions = load_ancestry_descriptions()
    names = {
        "human": "Człowiek",
        "automaton": "Automaton",
        "goblin": "Goblin",
        "dwarf": "Krasnolud",
        "orc": "Ork",
        "changeling": "Odmieniec",
        "swd_elf": "Elf (SWD Test)",
    }
    result = []
    for ancestry_id in ANCESTRIES:
        entry = descriptions.get(ancestry_id, {})
        source = entry.get("source", "PG") if isinstance(entry, dict) else "PG"
        result.append(
            {
                "id": ancestry_id,
                "name": names.get(ancestry_id, ancestry_id),
                "source": source,
            }
        )
    return result


def _creation_response(state: CreationState) -> dict:
    """Build the versioned JSON contract used by the component frontend."""
    _try_expand_current_group(state)
    finalize_defense(state.hero)
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
                state.hero,
                state.level_choices[state.choice_cursor : state.choice_cursor + 1],
                state.enabled_sources,
            ),
        },
    }
    if state.awaiting_equipment_pick():
        response["step"]["awaiting_equipment_pick"] = True
        response["step"]["equipment_store"] = _load_equipment_store()
        response["step"]["equipment_limits"] = {"armors": 1, "weapons": 5, "shields": 1}
        response["step"]["current_equipment"] = {
            "armors": [a.model_dump(mode="json") for a in state.hero.equipment.armors],
            "weapons": [w.model_dump(mode="json") for w in state.hero.equipment.weapons],
            "shields": [s.model_dump(mode="json") for s in state.hero.equipment.shields],
        }
    return response


@app.errorhandler(CreationError)
def invalid_creation(error):
    return jsonify({"error": str(error)}), error.status


def _repository():
    return app.config["CREATION_REPOSITORY"]


def _get_manual_creation(creation_id=None):
    identifier = creation_id or (request.view_args or {}).get("creation_id")
    identifier = identifier or session.get("active_creation_id")
    if not identifier:
        return None
    return _repository().get(_session_id(), identifier)


def _mutate_creation(model, command, creation_id, **kwargs):
    current = _get_manual_creation(creation_id)
    if current is None:
        raise CreationError("Creation not found", 404)
    if "level" in kwargs and kwargs["level"] != current.current_level:
        raise CreationError("Step is not active", 409)
    data = _request_data(model)
    state = CreationService(_repository()).mutate(
        _session_id(),
        creation_id,
        data["state_version"],
        lambda working: command(working, data, **kwargs),
    )
    result = _creation_response(state)
    if command is commands.rewind:
        result["invalidated_steps"] = state.invalidated_levels
    return jsonify(result)


@app.post("/api/creations")
def api_start_creation():
    state = commands.start_creation(_request_data(StartCreation))
    contract = _creation_response(state)
    _repository().create(_session_id(), state)
    session["active_creation_id"] = state.state_id
    return jsonify(contract)


@app.get("/api/creations/<creation_id>")
def api_get_creation(creation_id):
    state = _get_manual_creation(creation_id)
    if state is None:
        raise CreationError("Creation not found", 404)
    return jsonify(_creation_response(state))


@app.post("/api/creations/<creation_id>/steps/<int:level>/choices")
def api_apply_choices(creation_id, level):
    return _mutate_creation(ApplyChoices, commands.apply_choices, creation_id, level=level)


@app.post("/api/creations/<creation_id>/advance")
def api_advance_creation(creation_id):
    return _mutate_creation(VersionedRequest, commands.advance, creation_id)


@app.post("/api/creations/<creation_id>/paths/<tier>")
def api_pick_path(creation_id, tier):
    return _mutate_creation(PickPath, commands.pick_path, creation_id, tier=tier)


@app.post("/api/creations/<creation_id>/equipment")
def api_set_equipment(creation_id):
    return _mutate_creation(PickEquipment, commands.set_equipment, creation_id)


@app.post("/api/creations/<creation_id>/rewind")
def api_rewind_creation(creation_id):
    return _mutate_creation(Rewind, commands.rewind, creation_id)


@app.post("/api/creations/<creation_id>/rewind_choice")
def api_rewind_choice(creation_id):
    return _mutate_creation(VersionedRequest, commands.rewind_choice, creation_id)


@app.post("/api/creations/<creation_id>/finalize")
def api_finalize_creation(creation_id):
    state = _get_manual_creation(creation_id)
    if state is None:
        raise CreationError("Creation not found", 404)
    if state.pending_choices:
        raise CreationError("Creation has unresolved choices", 409)
    if not state.can_finalize:
        raise CreationError("Complete required paths and equipment before exporting", 409)
    fill_pdf(state.hero, _output_path())
    return jsonify(
        {
            "summary": state.hero.model_dump(mode="json"),
            "pdf_url": url_for("download_current"),
        }
    )


@app.route("/")
def index():
    descriptions = load_ancestry_descriptions()
    ancestry_list = load_ancestry_list()
    return render_template(
        "index.html",
        ancestry_descriptions=descriptions,
        ancestry_list=ancestry_list,
        novice_paths=load_novice_paths(),
        expert_paths=load_expert_paths(),
        master_paths=load_master_paths(),
    )


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


if __name__ == "__main__":
    app.run(debug=True)
