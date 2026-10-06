import pytest

from config import secret_key


def test_production_requires_a_secret(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY must be configured"):
        secret_key()


def test_development_uses_unpredictable_secrets(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    first = secret_key(development=True)
    assert len(first) == 64
    assert first != secret_key(development=True)


def test_configured_secret_is_preserved(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "configured-secret")
    assert secret_key() == "configured-secret"


def test_pdf_destination_never_uses_client_identifiers(raw_client, monkeypatch, tmp_path):
    monkeypatch.setattr("main.OUTPUT_DIR", tmp_path)
    contract = raw_client.post("/api/creations", json={"mode": "random", "ancestry": "human"}).json
    body = {"state_token": contract["state_token"], "state_version": 0}
    assert raw_client.post("/api/creations/wrong-character/finalize", json=body).status_code == 404
    assert list(tmp_path.iterdir()) == []
    response = raw_client.post(f"/api/creations/{contract['creation_id']}/finalize", json=body)
    assert response.data.startswith(b"%PDF-")
    assert list(tmp_path.iterdir()) == []
