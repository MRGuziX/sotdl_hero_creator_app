"""Tests for the REST API endpoints under /api/creations."""

import pytest


def _create_manual(client, ancestry="human"):
    response = client.post("/api/creations", json={"mode": "manual", "ancestry": ancestry})
    assert response.status_code == 200
    data = response.get_json()
    assert "state" in data
    return data


def _create_random(client, ancestry="human", level=0):
    response = client.post(
        "/api/creations",
        json={"mode": "random", "ancestry": ancestry, "target_level": level},
    )
    assert response.status_code == 200
    return response.get_json()


class TestStartCreation:
    def test_manual_creation_returns_state(self, client):
        data = _create_manual(client)
        state = data["state"]
        assert state["state_id"]
        assert state["current_level"] == 0
        assert state["mode"] == "manual"
        assert "state_version" in state

    def test_random_creation_returns_state(self, client):
        data = _create_random(client)
        state = data["state"]
        assert state["mode"] == "random"

    def test_invalid_ancestry_returns_400(self, client):
        response = client.post("/api/creations", json={"mode": "manual", "ancestry": "elf"})
        assert response.status_code == 400

    def test_invalid_mode_returns_400(self, client):
        response = client.post("/api/creations", json={"mode": "turbo", "ancestry": "human"})
        assert response.status_code == 400

    def test_random_invalid_level_returns_400(self, client):
        response = client.post(
            "/api/creations",
            json={"mode": "random", "ancestry": "human", "target_level": 99},
        )
        assert response.status_code == 400


class TestGetCreation:
    def test_get_existing_creation(self, client):
        data = _create_manual(client)
        state_id = data["state"]["state_id"]
        response = client.get(f"/api/creations/{state_id}")
        assert response.status_code == 200

    def test_get_missing_creation_returns_404(self, client):
        response = client.get("/api/creations/nonexistent")
        assert response.status_code == 404


class TestApplyChoices:
    def test_stale_version_returns_409(self, client):
        data = _create_manual(client)
        state = data["state"]
        if not state.get("level_choices"):
            pytest.skip("No choices at level 0 for this ancestry")
        response = client.post(
            f"/api/creations/{state['state_id']}/steps/0/choices",
            json={
                "selections": [state["level_choices"][0][0]],
                "choice_cursor": 0,
                "state_version": state["state_version"] + 999,
            },
        )
        assert response.status_code == 409

    def test_missing_selections_returns_400(self, client):
        data = _create_manual(client)
        state = data["state"]
        response = client.post(
            f"/api/creations/{state['state_id']}/steps/0/choices",
            json={"state_version": state["state_version"]},
        )
        assert response.status_code == 400

    def test_valid_choice_is_accepted(self, client):
        data = _create_manual(client)
        state = data["state"]
        if not state.get("level_choices"):
            pytest.skip("No choices at level 0")
        first_option = state["level_choices"][0][0]
        response = client.post(
            f"/api/creations/{state['state_id']}/steps/0/choices",
            json={
                "selections": [first_option],
                "choice_cursor": 0,
                "state_version": state["state_version"],
            },
        )
        assert response.status_code == 200


class TestPickPath:
    def test_invalid_path_id_with_traversal_returns_400(self, client):
        data = _create_manual(client)
        state = data["state"]
        response = client.post(
            f"/api/creations/{state['state_id']}/paths/novice",
            json={"path_id": "../../etc/passwd", "state_version": state["state_version"]},
        )
        result = response.get_json()
        assert response.status_code in (400, 409)
        if response.status_code == 400:
            assert "Invalid path_id" in result["error"]

    def test_invalid_tier_returns_400(self, client):
        data = _create_manual(client)
        state = data["state"]
        response = client.post(
            f"/api/creations/{state['state_id']}/paths/legendary",
            json={"path_id": "warrior", "state_version": state["state_version"]},
        )
        assert response.status_code == 400

    def test_missing_path_id_returns_400(self, client):
        data = _create_manual(client)
        state = data["state"]
        response = client.post(
            f"/api/creations/{state['state_id']}/paths/novice",
            json={"state_version": state["state_version"]},
        )
        assert response.status_code in (400, 409)


class TestRewind:
    def test_rewind_stale_version_returns_409(self, client):
        data = _create_manual(client)
        state = data["state"]
        response = client.post(
            f"/api/creations/{state['state_id']}/rewind",
            json={"target_level": 0, "state_version": state["state_version"] + 999},
        )
        assert response.status_code == 409

    def test_rewind_missing_creation_returns_404(self, client):
        response = client.post(
            "/api/creations/nonexistent/rewind",
            json={"target_level": 0, "state_version": 0},
        )
        assert response.status_code == 404


class TestRewindChoice:
    def test_rewind_choice_at_cursor_zero_returns_400(self, client):
        data = _create_manual(client)
        state = data["state"]
        response = client.post(
            f"/api/creations/{state['state_id']}/rewind_choice",
            json={"state_version": state["state_version"]},
        )
        assert response.status_code == 400

    def test_rewind_choice_stale_version_returns_409(self, client):
        data = _create_manual(client)
        state = data["state"]
        response = client.post(
            f"/api/creations/{state['state_id']}/rewind_choice",
            json={"state_version": state["state_version"] + 999},
        )
        assert response.status_code == 409


class TestFinalize:
    def test_finalize_missing_creation_returns_404(self, client):
        response = client.post("/api/creations/nonexistent/finalize")
        assert response.status_code == 404

    def test_finalize_with_unresolved_choices_returns_409(self, client):
        data = _create_manual(client)
        state = data["state"]
        if state.get("level_choices"):
            response = client.post(f"/api/creations/{state['state_id']}/finalize")
            assert response.status_code == 409
        else:
            pytest.skip("No pending choices to test against")
