import os
import random
import tempfile

from flask import Flask, render_template, send_file, redirect, url_for, request, jsonify

from utils.pdf_creator import fill_pdf
from utils.utils import get_hero

app = Flask(__name__, static_folder='pictures', static_url_path='/static')

ANCESTRIES = ["human", "automaton", "goblin", "dwarf", "orc", "changeling"]

# Use /tmp for serverless environment compatibility
OUTPUT_PATH = os.path.join(tempfile.gettempdir(), "hero_card.pdf")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/roll/<ancestry>')
def roll(ancestry):
    if ancestry not in ANCESTRIES:
        return "Invalid ancestry", 400

    # Check if download is requested
    download = request.args.get('download', '0') == '1'
    is_random = request.args.get('is_random', '1') == '1'

    if not download:
        # 1. Roll a character
        hero_data = get_hero(ancestry, is_random=is_random)

        if not is_random and hero_data.get("choices"):
            # If not random and there are choices, return choices as JSON
            return jsonify({
                "status": "need_choices",
                "hero_data": hero_data
            })

        # 2. Fill the PDF (if random, it's already done in get_hero)
        if not is_random:
            fill_pdf(hero_data, OUTPUT_PATH)

        print(hero_data)

        # 3. Return the filled PDF
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

    from utils.utils import change_choices_to_actions, bulk_update_attributes

    # Apply selected choices
    hero_data = change_choices_to_actions(hero_data, is_random=False, selected_choices=selected_choices)

    # Apply actions
    hero_data = bulk_update_attributes(hero_data, is_random=False)

    print(hero_data)

    # Fill the PDF
    fill_pdf(hero_data, OUTPUT_PATH)

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
