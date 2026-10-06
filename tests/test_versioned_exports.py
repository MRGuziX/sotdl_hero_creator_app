from models.action import AddAttribute
from utils.utils import apply_action


def test_healing_rate_tracks_health_and_bonuses(hero):
    assert hero.healing_rate == hero.health // 4
    apply_action(AddAttribute(name="health", value=12), hero, False)
    assert hero.healing_rate == hero.health // 4
    apply_action(AddAttribute(name="healing_rate", value=2), hero, False)
    assert hero.healing_rate == hero.health // 4 + 2


def test_export_returns_pdf_without_persistent_file_or_download_url(client, tmp_path, monkeypatch):
    monkeypatch.setattr("main.OUTPUT_DIR", tmp_path)
    contract = client.post("/api/creations", json={"mode": "random", "ancestry": "human"}).json
    cid = contract["creation_id"]
    finalized = client.post(f"/api/creations/{cid}/finalize", json={"state_version": 0})
    assert finalized.status_code == 200
    assert finalized.mimetype == "application/pdf"
    assert finalized.data.startswith(b"%PDF-")
    assert finalized.headers["Cache-Control"] == "no-store"
    assert list(tmp_path.iterdir()) == []
    assert client.get(f"/api/creations/{cid}/pdf/0").status_code == 404
    assert client.get("/download_current").status_code == 404


def test_finalize_rejects_stale_version(client):
    contract = client.post("/api/creations", json={"mode": "random", "ancestry": "human"}).json
    assert (
        client.post(
            f"/api/creations/{contract['creation_id']}/finalize", json={"state_version": 2}
        ).status_code
        == 409
    )
