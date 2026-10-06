import os
import subprocess
import sys

import pytest

from main import app
from domain.state_token import StateTokenSizeError


def start(client, **options):
    return client.post("/api/creations", json={"mode": "random", "ancestry": "human", **options})


def test_vercel_import_needs_no_database_or_writable_instance_directory(tmp_path):
    environment = dict(os.environ, VERCEL="1", SECRET_KEY="tests-only-secret")
    environment.pop("DATABASE_URL", None)
    environment["CREATION_DB_PATH"] = str(tmp_path / "must-not-create" / "db.sqlite3")
    result = subprocess.run(
        [sys.executable, "-c", "import main; print('ready')"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ready"
    assert not (tmp_path / "must-not-create").exists()
    assert "CREATION_REPOSITORY" not in app.config


def test_creation_resume_and_pdf_need_no_cookie_or_backend_storage(raw_client):
    response = start(raw_client)
    assert "Set-Cookie" not in response.headers
    contract = response.json
    path = f"/api/creations/{contract['creation_id']}"
    with app.test_client(use_cookies=False) as independent:
        resumed = independent.post(path + "/resume", json={"state_token": contract["state_token"]})
        assert resumed.status_code == 200
        assert resumed.json == contract
        pdf = independent.post(
            path + "/finalize", json={"state_token": contract["state_token"], "state_version": 0}
        )
        assert pdf.status_code == 200
        assert pdf.data.startswith(b"%PDF-")
        assert "Set-Cookie" not in pdf.headers
        assert independent.get(path).status_code == 404
        assert independent.get("/api/creations").status_code == 405


@pytest.mark.parametrize("suffix", ["resume", "advance", "cancel_advance", "rewind", "finalize"])
def test_id_alone_cannot_recover_or_change_a_character(raw_client, suffix):
    contract = start(raw_client).json
    response = raw_client.post(
        f"/api/creations/{contract['creation_id']}/{suffix}", json={"state_version": 0}
    )
    assert response.status_code == 400
    assert "state_token" in response.json["error"]


def test_forged_token_and_wrong_character_are_rejected(raw_client):
    contract = start(raw_client).json
    path = f"/api/creations/{contract['creation_id']}/resume"
    assert raw_client.post(path, json={"state_token": "forged"}).status_code == 410
    assert (
        raw_client.post(
            "/api/creations/another-character/resume", json={"state_token": contract["state_token"]}
        ).status_code
        == 404
    )


def test_body_size_limit_returns_json_without_reflecting_state(raw_client):
    response = raw_client.post(
        "/api/creations", data=b"x" * 1_500_001, content_type="application/json"
    )
    assert response.status_code == 413
    assert response.json == {"error": "Creation request is too large"}


def test_response_size_failure_keeps_the_previous_carried_state(raw_client, monkeypatch):
    contract = raw_client.post("/api/creations", json={"mode": "manual", "ancestry": "human"}).json

    def too_large(self, state):
        raise StateTokenSizeError("Too large")

    with monkeypatch.context() as patch:
        patch.setattr("domain.state_token.StateTokenCodec.encode", too_large)
        response = raw_client.post(
            f"/api/creations/{contract['creation_id']}/steps/0/choices",
            json={
                "state_token": contract["state_token"],
                "state_version": 0,
                "selections": [contract["state"]["pending_choices"][0][0]],
                "choice_cursor": 0,
            },
        )
        assert response.status_code == 413
    restored = raw_client.post(
        f"/api/creations/{contract['creation_id']}/resume",
        json={"state_token": contract["state_token"]},
    )
    assert restored.json == contract


def test_full_manual_magic_lifecycle_fits_transport_and_exports_filled_pdf(client):
    from io import BytesIO
    from pypdf import PdfReader

    contract = client.post("/api/creations", json={"mode": "manual", "ancestry": "human"}).json
    path = f"/api/creations/{contract['creation_id']}"
    for _ in range(250):
        state = contract["state"]
        assert len(contract["state_token"]) < 100_000
        body = {"state_version": state["state_version"]}
        if state["pending_choices"]:
            suffix = f"steps/{state['current_level']}/choices"
            body.update(
                selections=[state["pending_choices"][0][0]], choice_cursor=state["choice_cursor"]
            )
        elif state["awaiting_path_pick"]:
            tier = state["awaiting_path_pick"]
            suffix = "paths/" + tier
            body["path_id"] = {"novice": "mage", "expert": "wizard", "master": "aeromancer"}[tier]
        elif state["awaiting_equipment_pick"]:
            suffix = "equipment"
        elif state["current_level"] < 10:
            suffix = "advance"
        else:
            break
        response = client.post(path + "/" + suffix, json=body)
        assert response.status_code == 200, response.json
        contract = response.json
    else:
        pytest.fail("Wizard did not complete")
    assert state["current_level"] == 10 and state["can_finalize"]
    assert state["hero"]["spells"]
    response = client.post(path + "/finalize", json={"state_version": state["state_version"]})
    assert response.status_code == 200
    assert len(response.data) < 4_500_000
    reader = PdfReader(BytesIO(response.data))
    assert len(reader.pages) >= 3
    fields = reader.get_fields()
    assert fields["ancestry"]["/V"] == "Człowiek"


def test_render_failure_cleans_request_scratch_and_original_token_is_reusable(
    raw_client, monkeypatch, tmp_path
):
    monkeypatch.setattr("main.OUTPUT_DIR", tmp_path)
    contract = start(raw_client).json

    def fail(hero, destination):
        destination.write_bytes(b"partial")
        raise RuntimeError("Renderer failed")

    monkeypatch.setattr("main.export_pdf", fail)
    with pytest.raises(RuntimeError, match="Renderer failed"):
        raw_client.post(
            f"/api/creations/{contract['creation_id']}/finalize",
            json={"state_token": contract["state_token"], "state_version": 0},
        )
    assert list(tmp_path.iterdir()) == []
    resumed = raw_client.post(
        f"/api/creations/{contract['creation_id']}/resume",
        json={"state_token": contract["state_token"]},
    )
    assert resumed.json == contract
