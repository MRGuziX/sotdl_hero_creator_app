import os

import pytest

from main import app, OUTPUT_PATH


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_index_route(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"cwd_logo.png" in response.data


def test_roll_ancestry_route(client):
    ancestries = ["human", "automaton", "goblin", "dwarf", "orc", "changeling"]
    for ancestry in ancestries:
        response = client.get(f'/roll/{ancestry}')
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/pdf'


def test_roll_invalid_ancestry(client):
    response = client.get('/roll/elf')
    assert response.status_code == 400
    assert b"Invalid ancestry" in response.data


def test_roll_random_route(client):
    response = client.get('/roll_random', follow_redirects=True)
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/pdf'


def test_static_logo(client):
    response = client.get('/static/cwd_logo.png')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'image/png'


def test_download_current_route(client):
    client.get('/roll/human')

    response = client.get('/download_current')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/pdf'


def test_download_no_hero(client):
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


def test_roll_manual_returns_choices(client):
    response = client.get('/roll/human?is_random=0')
    assert response.status_code == 200
    data = response.get_json()
    if data and data.get("status") == "need_choices":
        assert "hero_data" in data
        assert "choices" in data


def test_confirm_choices(client):
    response = client.get('/roll/human?is_random=0')
    data = response.get_json()

    if data and data.get("status") == "need_choices":
        hero_data = data["hero_data"]
        choices = data["choices"]
        selected = [group[0] for group in choices]

        response = client.post('/confirm_choices', json={
            "hero_data": hero_data,
            "selected_choices": selected,
        })
        assert response.status_code == 200
        result = response.get_json()
        assert result["status"] == "success"
