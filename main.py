import json
import logging
import os
import random
import tempfile
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, send_file, url_for

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)

from models.action import Action
from models.base_hero import AncestryHero
from utils.pdf_creator import fill_pdf
from utils.utils import apply_action, get_hero, resolve_choices
from utils.utils import get_spells_for_tradition, get_tradition_name_from_talent, _load_json

app = Flask(__name__, static_folder='pictures', static_url_path='/static')

ANCESTRIES = ["human", "automaton", "goblin", "dwarf", "orc", "changeling"]

OUTPUT_PATH = os.path.join(tempfile.gettempdir(), "hero_card.pdf")
DESCRIPTIONS_PATH = os.path.join("data_base", "ancestry", "descriptions.json")
NOVICE_PATHS_DIR = Path("data_base/paths/novice")


def load_novice_paths():
    paths = []
    for path_file in sorted(NOVICE_PATHS_DIR.glob("*.json")):
        if path_file.name == "cleric_religions.json":
            continue
        path_data = _load_json(str(path_file))
        if "path_name" in path_data and "level_benefits" in path_data:
            paths.append({"id": path_file.stem, "name": path_data["path_name"]})
    return paths


def choice_context(hero, choices):
    """Return the lists needed to make tradition and spell choices explicit."""
    traditions = sorted({
        get_tradition_name_from_talent(t.name)
        for t in hero.talents
        if get_tradition_name_from_talent(t.name)
    })
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


def choices_response(hero, choices, choice_cursor=0):
    return {
        "choices": [[a.model_dump() for a in choices[0]]] if choices else [],
        "choice_cursor": choice_cursor,
        **choice_context(hero, choices[:1]),
    }


def load_ancestry_descriptions():
    with open(DESCRIPTIONS_PATH, "r", encoding="utf-8") as descriptions_file:
        return json.load(descriptions_file)


@app.route('/')
def index():
    descriptions = load_ancestry_descriptions()
    return render_template(
        'index.html',
        ancestry_descriptions=descriptions,
        novice_paths=load_novice_paths(),
    )


@app.route('/roll/<ancestry>')
def roll(ancestry):
    if ancestry not in ANCESTRIES:
        return "Invalid ancestry", 400

    download = request.args.get('download', '0') == '1'
    is_random = request.args.get('is_random', '1') == '1'
    level = int(request.args.get('level', '0'))
    path_name = request.args.get('path')

    if not download:
        result = get_hero(ancestry, is_random=is_random, level=level, path_name=path_name)

        if isinstance(result, tuple):
            hero, choices = result
            return jsonify({
                "status": "need_choices",
                "hero_data": hero.model_dump(),
                # Manual creation is intentionally a wizard: expose only the
                # next unresolved choice so later choices see earlier picks.
                **choices_response(hero, choices),
            })

        hero = result
        if not is_random:
            fill_pdf(hero, OUTPUT_PATH)

    return send_file(
        OUTPUT_PATH,
        as_attachment=download,
        download_name=f"{ancestry}_hero.pdf",
        mimetype='application/pdf'
    )


@app.route('/confirm_choices', methods=['POST'])
def confirm_choices():
    data = request.get_json(silent=True) or {}
    hero_data = data.get('hero_data')
    selected_choices = data.get('selected_choices')
    choice_cursor = data.get('choice_cursor', 0)

    if not hero_data or not selected_choices or not isinstance(choice_cursor, int) or choice_cursor < 0:
        return "Missing data", 400

    try:
        hero = AncestryHero.model_validate(hero_data)
    except (TypeError, ValueError):
        return "Invalid hero data", 400

    parsed_choices = []
    try:
        from pydantic import TypeAdapter
        action_adapter = TypeAdapter(Action)
        for choice in selected_choices:
            parsed_choices.append(action_adapter.validate_python(choice))
    except (TypeError, ValueError):
        return "Invalid choice", 400

    for action in parsed_choices:
        apply_action(action, hero, is_random=False)

    # Re-evaluate choices in case new ones appeared (e.g. religion-dependent traditions)
    from utils.utils import build_hero, expand_any_to_choices
    
    # We need to get the original benefits to see what's left
    _, actions, choices = build_hero(hero.ancestry_id, level=hero.level, path_name=hero.path_name)
    
    # Re-expand choices based on the current hero state (which now has religion, etc.)
    remaining_actions, remaining_choices = expand_any_to_choices(hero, actions, choices)
    # The browser always receives and submits exactly the first unresolved
    # group. Re-expansion may recreate identical option values (for example
    # for several `add_attribute(any)` actions), so value-based matching is
    # ambiguous and can make the wizard loop. Advance the explicit cursor.
    next_cursor = choice_cursor + 1
    filtered_choices = remaining_choices[next_cursor:] if remaining_choices else []

    if filtered_choices:
        return jsonify({
            "status": "need_choices",
            "hero_data": hero.model_dump(),
            **choices_response(hero, filtered_choices, next_cursor),
        })
    
    fill_pdf(hero, OUTPUT_PATH)
    return jsonify({"status": "success", "download_url": url_for('download_current')})


@app.route('/roll_random')
def roll_random():
    random_ancestry = random.choice(ANCESTRIES)
    return redirect(url_for('roll', ancestry=random_ancestry, **request.args))


@app.route('/download_current')
def download_current():
    if not os.path.exists(OUTPUT_PATH):
        return "No hero generated yet", 404

    download = request.args.get('download', '0') == '1'

    return send_file(
        OUTPUT_PATH,
        as_attachment=download,
        download_name="hero_card.pdf",
        mimetype='application/pdf'
    )


if __name__ == '__main__':
    app.run(debug=True)
