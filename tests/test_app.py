import pytest
import os
from main import app, OUTPUT_PATH

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_route(client):
    """Test if the index page loads successfully."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"cwd_logo.png" in response.data

def test_roll_ancestry_route(client):
    """Test if the roll ancestry route generates a PDF."""
    ancestries = ["human", "automaton", "goblin", "dwarf", "orc", "changeling"]
    for ancestry in ancestries:
        response = client.get(f'/roll/{ancestry}')
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/pdf'
        assert f'{ancestry}_hero.pdf' in response.headers['Content-Disposition']

def test_roll_invalid_ancestry(client):
    """Test if an invalid ancestry returns a 400 error."""
    response = client.get('/roll/elf')
    assert response.status_code == 400
    assert b"Invalid ancestry" in response.data

def test_roll_random_route(client):
    """Test if the roll random route redirects correctly."""
    response = client.get('/roll_random', follow_redirects=True)
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/pdf'

def test_static_logo(client):
    """Test if the logo is served from static directory."""
    response = client.get('/static/cwd_logo.png')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'image/png'

def test_static_ancestry_button(client):
    """Test if the ancestry button image is served from static directory."""
    response = client.get('/static/ancestry_button.png')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'image/png'

def test_download_current_route(client):
    """Test if the download current route returns the last generated PDF."""
    # 1. Generate a hero
    client.get('/roll/human')
    
    # 2. Test download current
    response = client.get('/download_current')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/pdf'
    assert 'attachment' in response.headers['Content-Disposition']
    assert 'hero_card.pdf' in response.headers['Content-Disposition']

def test_download_no_hero(client):
    """Test if download current returns 404 if no hero exists."""
    import os
    
    # Temporarily rename file if it exists
    backup_path = OUTPUT_PATH + ".bak"
    exists = os.path.exists(OUTPUT_PATH)
    if exists:
        os.rename(OUTPUT_PATH, backup_path)
    
    try:
        response = client.get('/download_current')
        assert response.status_code == 404
        assert b"No hero generated yet" in response.data
    finally:
        if exists:
            if os.path.exists(OUTPUT_PATH):
                os.remove(OUTPUT_PATH)
            os.rename(backup_path, OUTPUT_PATH)

def test_roll_with_download_param(client):
    """Test if roll with download=1 returns attachment without re-rolling."""
    # This is hard to test without complex mocks, but let's check basic response.
    response = client.get('/roll/human?download=1')
    assert response.status_code == 200
    assert 'attachment' in response.headers['Content-Disposition']
    assert 'human_hero.pdf' in response.headers['Content-Disposition']
