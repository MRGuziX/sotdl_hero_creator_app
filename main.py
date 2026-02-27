import os
import random
import tempfile

from flask import Flask, render_template, send_file, redirect, url_for, request

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

    if not download:
        # 1. Roll a character (only if not downloading existing one)
        hero_data = get_hero(ancestry)

        # 2. Fill the PDF
        fill_pdf(hero_data, OUTPUT_PATH)

    # 3. Return the filled PDF
    return send_file(
        OUTPUT_PATH,
        as_attachment=download,
        download_name=f"{ancestry}_hero.pdf",
        mimetype='application/pdf'
    )


@app.route('/roll_random')
def roll_random():
    random_ancestry = random.choice(ANCESTRIES)
    return redirect(url_for('roll', ancestry=random_ancestry, **request.args))


@app.route('/download_current')
def download_current():
    if not os.path.exists(OUTPUT_PATH):
        return "No hero generated yet", 404

    return send_file(
        OUTPUT_PATH,
        as_attachment=True,
        download_name="hero_card.pdf",
        mimetype='application/pdf'
    )


if __name__ == '__main__':
    app.run(debug=True)
