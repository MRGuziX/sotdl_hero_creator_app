from pathlib import Path

import pytest

import main
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


@pytest.mark.parametrize("identifier", ["../../outside", "/tmp/outside", None, 123, {}])
def test_forged_pdf_identifiers_are_rejected(client, identifier):
    with client.session_transaction() as browser_session:
        browser_session["creation_id"] = identifier
    response = client.get("/download_current")
    assert response.status_code == 400


def test_pdf_symlink_cannot_escape_output_directory(client, monkeypatch, tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    identifier = "a" * 32
    external = tmp_path / "outside.pdf"
    external.touch()
    (output / f"{identifier}.pdf").symlink_to(external)
    monkeypatch.setattr(main, "OUTPUT_DIR", output)
    with client.session_transaction() as browser_session:
        browser_session["creation_id"] = identifier
    assert client.get("/download_current").status_code == 400


def test_pdf_path_is_session_scoped(client, monkeypatch, tmp_path):
    monkeypatch.setattr(main, "OUTPUT_DIR", tmp_path)
    with client.session_transaction() as browser_session:
        browser_session["creation_id"] = "b" * 32
    client.get("/download_current")
    assert Path(main._output_path()) == tmp_path / f"{'b' * 32}.pdf"
