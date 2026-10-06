import logging
import tempfile
from pathlib import Path
from io import BytesIO

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_file,
    send_from_directory,
)
from pydantic import ValidationError

from config import secret_key
from domain import creation_service as commands
from domain.creation_service import CreationError, mutate_creation, _try_expand_current_group

from domain.creation_state import CreationState, CreationStateError
from domain.state_token import StateTokenCodec, StateTokenSizeError
from models.action import (
    Action,
)
from models.base_hero import AncestryHero
from models.requests import (
    ApplyChoices,
    CarriedStateRequest,
    PickEquipment,
    PickPath,
    Rewind,
    StartCreation,
    VersionedRequest,
)
from export.pdf import export_pdf
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
# Keep browser-carried state requests below Vercel's payload limit.
app.config["MAX_CONTENT_LENGTH"] = 1_500_000


@app.route("/assets/<path:filename>")
def assets(filename):
    """Serve extracted presentation assets without changing legacy image URLs."""
    return send_from_directory(PROJECT_ROOT / "static", filename)


ANCESTRIES = ["human", "automaton", "goblin", "dwarf", "orc", "changeling", "swd_elf"]

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = Path(tempfile.gettempdir()) / "sotdl_hero_creator"
DESCRIPTIONS_PATH = PROJECT_ROOT / "data_base" / "ancestry" / "descriptions.json"
NOVICE_PATHS_DIR = PROJECT_ROOT / "data_base" / "paths" / "novice"
EXPERT_PATHS_DIR = PROJECT_ROOT / "data_base" / "paths" / "expert"
MASTER_PATHS_DIR = PROJECT_ROOT / "data_base" / "paths" / "master"


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


def _token_codec():
    return StateTokenCodec(app.secret_key)


@app.errorhandler(413)
def oversized_request(error):
    return jsonify({"error": "Creation request is too large"}), 413


@app.errorhandler(StateTokenSizeError)
def oversized_creation(error):
    return jsonify(
        {"error": "Creation is too large. Download the current PDF before continuing."}
    ), 413


@app.after_request
def private_creation_responses(response):
    if request.path.startswith("/api/creations"):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
    return response


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
            description = (path_data.get("path_description") or "").strip()
            tier_name = {"novice": "Nowicjusza", "expert": "Eksperta", "master": "Mistrza"}[
                directory.name
            ]
            entry["description"] = description or (
                f"{path_data['path_name']} — ścieżka {tier_name}. "
                "Opis fabularny w przygotowaniu (szablon tymczasowy)."
            )
            paths.append(entry)
    return paths


def load_novice_paths() -> list[dict[str, str]]:
    return _load_paths(NOVICE_PATHS_DIR, skip={"cleric_religions.json"})


def load_expert_paths() -> list[dict[str, str]]:
    return _load_paths(EXPERT_PATHS_DIR)


def load_master_paths() -> list[dict[str, str]]:
    return _load_paths(MASTER_PATHS_DIR)


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
    return _load_json(str(DESCRIPTIONS_PATH))


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
    response["state_token"] = _token_codec().encode(state)
    return response


@app.errorhandler(CreationError)
def invalid_creation(error):
    return jsonify({"error": str(error)}), error.status


@app.errorhandler(CreationStateError)
def incompatible_creation(error):
    return jsonify(
        {"error": "This browser draft is invalid or incompatible. Start a new character."}
    ), 410


def _carried_creation(creation_id, data):
    state = _token_codec().decode(data["state_token"])
    if state.state_id != creation_id:
        raise CreationError("Creation token does not match this character", 404)
    return state


def _mutate_creation(model, command, creation_id, **kwargs):
    current = _carried_creation(creation_id, _request_data(CarriedStateRequest))
    if "level" in kwargs and kwargs["level"] != current.current_level:
        raise CreationError("Step is not active", 409)
    data = _request_data(model)
    state = mutate_creation(
        current,
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
    return jsonify(contract)


@app.post("/api/creations/<creation_id>/resume")
def api_resume_creation(creation_id):
    state = _carried_creation(creation_id, _request_data(CarriedStateRequest))
    return jsonify(_creation_response(state))


@app.post("/api/creations/<creation_id>/steps/<int:level>/choices")
def api_apply_choices(creation_id, level):
    return _mutate_creation(ApplyChoices, commands.apply_choices, creation_id, level=level)


@app.post("/api/creations/<creation_id>/advance")
def api_advance_creation(creation_id):
    return _mutate_creation(VersionedRequest, commands.advance, creation_id)


@app.post("/api/creations/<creation_id>/cancel_advance")
def api_cancel_advance_creation(creation_id):
    return _mutate_creation(VersionedRequest, commands.cancel_advance, creation_id)


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
    data = _request_data(VersionedRequest)
    state = _carried_creation(creation_id, data)
    if data["state_version"] != state.state_version:
        raise CreationError("Creation changed; refresh before exporting", 409)
    if state.pending_choices:
        raise CreationError("Creation has unresolved choices", 409)
    if not state.can_finalize:
        raise CreationError("Complete required paths and equipment before exporting", 409)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="export-", dir=OUTPUT_DIR) as scratch:
        output = export_pdf(state.hero, Path(scratch) / "hero.pdf")
        content = BytesIO(output.read_bytes())
    return send_file(
        content,
        as_attachment=False,
        download_name="hero_card.pdf",
        mimetype="application/pdf",
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


if __name__ == "__main__":
    app.run(debug=True)
