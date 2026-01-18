from flask import Flask, render_template, request, send_file
from utils.pdf_creator import fill_pdf
import os

from utils.utils import build_hero

app = Flask(__name__)

@app.route('/')
def index():
    ancestries = ["Człowiek", "Ork", "Goblin", "Automaton", "Krasnolud"]
    return render_template('index.html', ancestries=ancestries)

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    # 1. Get ancestry from form
    ancestry_label = request.form.get('ancestry')
    mapping = {"Człowiek": "human", "Ork": "orc", "Goblin": "goblin", "Automaton": "automaton", "Krasnolud": "dwarf"}
    internal_key = mapping.get(ancestry_label)

    # 2. Build the hero data
    hero_data = build_hero(ancestry=internal_key)

    # 3. Path to your template (create this file in your project)
    template_path = os.path.join("utils", "hero_template.pdf")

    # 4. Fill the PDF
    pdf_buffer = fill_pdf(hero_data, template_path)

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"{ancestry_label}_bohater.pdf",
        mimetype='application/pdf'
    )

if __name__ == '__main__':
    app.run(debug=True)