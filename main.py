import json
import logging
import os
import random
import tempfile

from flask import Flask, render_template, send_file, redirect, url_for, request, jsonify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)

from models.action import Action
from models.base_hero import AncestryHero
from utils.pdf_creator import fill_pdf
from utils.utils import get_hero, resolve_choices, apply_action

app = Flask(__name__, static_folder='pictures', static_url_path='/static')

ANCESTRIES = ["human", "automaton", "goblin", "dwarf", "orc", "changeling"]

OUTPUT_PATH = os.path.join(tempfile.gettempdir(), "hero_card.pdf")
DESCRIPTIONS_PATH = os.path.join("data_base", "ancestry", "descriptions.json")


def load_ancestry_descriptions():
    with open(DESCRIPTIONS_PATH, "r", encoding="utf-8") as descriptions_file:
        return json.load(descriptions_file)


@app.route('/')
def index():
    descriptions = load_ancestry_descriptions()
    return render_template('index.html', ancestry_descriptions=descriptions)


@app.route('/roll/<ancestry>')
def roll(ancestry):
    if ancestry not in ANCESTRIES:
        return "Invalid ancestry", 400

    download = request.args.get('download', '0') == '1'
    is_random = request.args.get('is_random', '1') == '1'

    if not download:
        result = get_hero(ancestry, is_random=is_random)

        if isinstance(result, tuple):
            hero, choices = result
            return jsonify({
                "status": "need_choices",
                "hero_data": hero.model_dump(),
                "choices": [[a.model_dump() for a in group] for group in choices],
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
    data = request.json
    hero_data = data.get('hero_data')
    selected_choices = data.get('selected_choices')

    if not hero_data or selected_choices is None:
        return "Missing data", 400

    hero = AncestryHero.model_validate(hero_data)

    parsed_choices = []
    for choice in selected_choices:
        from pydantic import TypeAdapter
        action_adapter = TypeAdapter(Action)
        parsed_choices.append(action_adapter.validate_python(choice))

    for action in parsed_choices:
        apply_action(action, hero, is_random=False)

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
