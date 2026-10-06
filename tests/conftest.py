import os

import pytest
from flask.testing import FlaskClient

os.environ.setdefault("SECRET_KEY", "tests-only-secret-not-for-deployment")

from main import app
from models.base_hero import AncestryHero


class BrowserClient(FlaskClient):
    """Emulate the UI carrying its latest token, never server-side persistence.

    Workflow tests focus on commands. Security/transport tests use a plain
    FlaskClient to verify missing, forged and mismatched tokens.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.drafts = {}

    def open(self, *args, **kwargs):
        path = args[0] if args and isinstance(args[0], str) else kwargs.get("path", "")
        if kwargs.get("method", "GET").upper() == "POST" and path.startswith("/api/creations/"):
            identifier = path.split("/")[3]
            draft = self.drafts.get(identifier)
            if draft and "data" not in kwargs:
                payload = kwargs.get("json")
                if payload is None and path.endswith("/finalize"):
                    payload = {"state_version": draft["state"]["state_version"]}
                if isinstance(payload, dict):
                    kwargs["json"] = {"state_token": draft["state_token"], **payload}
        response = super().open(*args, **kwargs)
        if response.status_code == 200 and response.is_json:
            payload = response.get_json()
            if isinstance(payload, dict) and "state_token" in payload:
                self.drafts[payload["creation_id"]] = payload
        return response

    def resume(self, path):
        return self.post(path + "/resume", json={})


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with BrowserClient(app) as test_client:
        yield test_client


@pytest.fixture
def raw_client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def hero():
    return AncestryHero(
        ancestry_name="Człowiek",
        ancestry_id="human",
        strength=10,
        dexterity=10,
        intelligence=10,
        will=10,
        perception=10,
        defense=10,
        health=10,
        healing_rate=1,
        size=[1.0, 1.0],
        speed=10,
    )
