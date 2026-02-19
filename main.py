from flask import Flask, render_template, send_file, redirect, url_for, request
import random
import os
from utils.utils import get_hero
from utils.pdf_creator import fill_pdf

app = Flask(__name__, static_folder='pictures', static_url_path='/static')

ANCESTRIES = ["human", "automaton", "goblin", "dwarf", "orc", "changeling"]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/roll/<ancestry>')
def roll(ancestry):
    if ancestry not in ANCESTRIES:
        return "Invalid ancestry", 400
    
    # Check if download is requested
    download = request.args.get('download', '0') == '1'
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(project_root, "output", "hero_card.pdf")

    if not download:
        # 1. Roll a character (only if not downloading existing one)
        hero_data = get_hero(ancestry)
        
        # 2. Define output path (ensure output directory exists)
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # 3. Fill the PDF
        fill_pdf(hero_data, output_path)
    
    # 4. Return the filled PDF
    return send_file(
        output_path,
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
    project_root = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(project_root, "output", "hero_card.pdf")
    if not os.path.exists(output_path):
        return "No hero generated yet", 404
    
    return send_file(
        output_path,
        as_attachment=True,
        download_name="hero_card.pdf",
        mimetype='application/pdf'
    )

if __name__ == '__main__':
    app.run(debug=True)