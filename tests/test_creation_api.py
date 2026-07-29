"""Coverage for the JSON creation API used by the component-based wizard."""

import pytest

from main import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def _start(client, ancestry="human", mode="manual", target_level=0, paths=None):
    payload = {"mode": mode, "ancestry": ancestry}
    if mode == "random":
        payload["target_level"] = target_level
        payload["paths"] = paths or {}
    response = client.post("/api/creations", json=payload)
    assert response.status_code == 200
    return response.get_json()


def _resolve_all_choices(client, creation_id, state):
    while state["pending_choices"]:
        group = state["pending_choices"][0]
        response = client.post(
            f"/api/creations/{creation_id}/steps/{state['current_level']}/choices",
            json={
                "selections": [group[0]],
                "expected_cursor": state["choice_cursor"],
                "choice_cursor": state["choice_cursor"],
                "state_version": state["state_version"],
            },
        )
        assert response.status_code == 200
        payload = response.get_json()
        state = payload["state"]
    return state


def _advance(client, creation_id, state):
    response = client.post(
        f"/api/creations/{creation_id}/advance",
        json={"state_version": state["state_version"]},
    )
    assert response.status_code == 200
    payload = response.get_json()
    return payload["state"], payload["step"]


def _pick_path(client, creation_id, state, tier, path_id):
    response = client.post(
        f"/api/creations/{creation_id}/paths/{tier}",
        json={"path_id": path_id, "state_version": state["state_version"]},
    )
    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    return payload["state"], payload["step"]


def test_start_creation_rejects_invalid_mode(client):
    response = client.post(
        "/api/creations", json={"mode": "bogus", "ancestry": "human"}
    )
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_start_creation_rejects_unsupported_ancestry(client):
    response = client.post(
        "/api/creations", json={"mode": "manual", "ancestry": "elf"}
    )
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_start_creation_rejects_invalid_target_level_in_random_mode(client):
    response = client.post(
        "/api/creations",
        json={"mode": "random", "ancestry": "human", "target_level": 42},
    )
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_start_creation_manual_mode_ignores_target_level_and_starts_at_zero(client):
    # Manual mode always starts at level 0 with only the ancestry decided;
    # target_level (a random-mode-only concept) is dropped entirely.
    response = client.post(
        "/api/creations",
        json={"mode": "manual", "ancestry": "human", "target_level": 5, "path": "warrior"},
    )
    assert response.status_code == 200
    contract = response.get_json()
    assert contract["state"]["current_level"] == 0
    assert contract["step"]["level"] == 0
    assert contract["state"]["awaiting_path_pick"] is None


def test_start_creation_happy_path_returns_contract(client):
    contract = _start(client)
    assert "creation_id" in contract
    assert contract["state"]["current_level"] == 0
    assert contract["state"]["mode"] == "manual"
    assert contract["step"]["level"] == 0
    assert "required_complete" in contract["state"]
    assert "can_finalize" in contract["state"]
    assert "can_advance" in contract["state"]
    assert "awaiting_path_pick" in contract["state"]


def test_get_creation_returns_current_state(client):
    contract = _start(client)
    response = client.get(f"/api/creations/{contract['creation_id']}")
    assert response.status_code == 200
    assert response.get_json()["creation_id"] == contract["creation_id"]


def test_get_creation_missing_returns_404(client):
    response = client.get("/api/creations/does-not-exist")
    assert response.status_code == 404


def test_apply_choices_happy_path_advances_state(client):
    contract = _start(client)
    state = contract["state"]
    assert state["pending_choices"], "human level 0 should expose its own choices"

    group = state["pending_choices"][0]
    response = client.post(
        f"/api/creations/{contract['creation_id']}/steps/{state['current_level']}/choices",
        json={
            "selections": [group[0]],
            "expected_cursor": state["choice_cursor"],
            "choice_cursor": state["choice_cursor"],
            "state_version": state["state_version"],
        },
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert "state" in payload
    assert payload["state"]["state_version"] > state["state_version"]


def test_apply_choices_rejects_stale_state_version(client):
    contract = _start(client)
    state = contract["state"]
    group = state["pending_choices"][0]
    response = client.post(
        f"/api/creations/{contract['creation_id']}/steps/{state['current_level']}/choices",
        json={
            "selections": [group[0]],
            "expected_cursor": state["choice_cursor"],
            "choice_cursor": state["choice_cursor"],
            "state_version": state["state_version"] + 1,
        },
    )
    assert response.status_code == 409
    assert "Stale state" in response.get_json()["error"]


def test_apply_choices_rejects_inactive_step(client):
    contract = _start(client)
    response = client.post(
        f"/api/creations/{contract['creation_id']}/steps/5/choices",
        json={"selections": [], "state_version": 0},
    )
    assert response.status_code == 409
    assert "Step is not active" in response.get_json()["error"]


def test_apply_choices_missing_creation_returns_404(client):
    response = client.post(
        "/api/creations/does-not-exist/steps/0/choices",
        json={"selections": [], "state_version": 0},
    )
    assert response.status_code == 404


def test_apply_choices_completes_level_and_exposes_crossroads(client):
    contract = _start(client)
    state = _resolve_all_choices(client, contract["creation_id"], contract["state"])
    assert state["pending_choices"] == []
    assert state["required_complete"] is True
    assert state["can_finalize"] is True
    assert state["can_advance"] is True
    assert 0 in state["completed_steps"]


def test_rewind_rejects_target_beyond_current_level(client):
    contract = _start(client)
    response = client.post(
        f"/api/creations/{contract['creation_id']}/rewind", json={"target_level": 5}
    )
    assert response.status_code == 400


def test_rewind_rejects_negative_target(client):
    contract = _start(client)
    response = client.post(
        f"/api/creations/{contract['creation_id']}/rewind", json={"target_level": -1}
    )
    assert response.status_code == 400


def test_rewind_missing_creation_returns_404(client):
    response = client.post(
        "/api/creations/does-not-exist/rewind", json={"target_level": 0}
    )
    assert response.status_code == 404


def test_rewind_happy_path_invalidates_later_levels(client):
    contract = _start(client)
    state = _resolve_all_choices(client, contract["creation_id"], contract["state"])
    state, _ = _advance(client, contract["creation_id"], state)

    response = client.post(
        f"/api/creations/{contract['creation_id']}/rewind", json={"target_level": 0}
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["state"]["current_level"] == 0
    assert 1 in payload["invalidated_steps"]


def test_finalize_blocks_when_choices_are_pending(client):
    contract = _start(client)
    assert contract["state"]["pending_choices"]

    response = client.post(f"/api/creations/{contract['creation_id']}/finalize")
    assert response.status_code == 409
    assert "unresolved choices" in response.get_json()["error"]


def test_finalize_missing_creation_returns_404(client):
    response = client.post("/api/creations/does-not-exist/finalize")
    assert response.status_code == 404


def test_finalize_happy_path_returns_pdf_url_below_level_ten(client):
    # Finalize/preview must be available as soon as a hero exists with no
    # pending choices, not only once level 10 is reached.
    contract = _start(client)
    state = _resolve_all_choices(client, contract["creation_id"], contract["state"])
    assert state["current_level"] == 0

    response = client.post(f"/api/creations/{contract['creation_id']}/finalize")
    assert response.status_code == 200
    payload = response.get_json()
    assert "summary" in payload
    assert "pdf_url" in payload


def test_step_response_exposes_magic_context(client):
    contract = _start(client)
    assert "known_traditions" in contract["step"]
    assert "available_traditions" in contract["step"]
    assert "spells_by_tradition" in contract["step"]


def test_step_response_exposes_choice_counter(client):
    # Backstory rolls are randomized even in manual mode, so the exact
    # number of level 0 choice groups can vary between runs; only the
    # counter's internal consistency is asserted here.
    contract = _start(client)
    assert contract["step"]["total_choices_in_level"] >= 1
    assert contract["step"]["current_choice_index"] == 1


def test_advance_rejects_when_pending_choices_remain(client):
    contract = _start(client)
    response = client.post(
        f"/api/creations/{contract['creation_id']}/advance",
        json={"state_version": contract["state"]["state_version"]},
    )
    assert response.status_code == 409


def test_advance_rejects_stale_state_version(client):
    contract = _start(client)
    state = _resolve_all_choices(client, contract["creation_id"], contract["state"])
    response = client.post(
        f"/api/creations/{contract['creation_id']}/advance",
        json={"state_version": state["state_version"] + 1},
    )
    assert response.status_code == 409


def test_advance_missing_creation_returns_404(client):
    response = client.post(
        "/api/creations/does-not-exist/advance", json={"state_version": 0}
    )
    assert response.status_code == 404


def test_advance_moves_exactly_one_level_and_flags_novice_path_pick(client):
    contract = _start(client)
    state = _resolve_all_choices(client, contract["creation_id"], contract["state"])

    state, step = _advance(client, contract["creation_id"], state)
    assert state["current_level"] == 1
    assert state["awaiting_path_pick"] == "novice"
    assert step["awaiting_path_pick"] == "novice"


def test_pick_path_rejects_unsupported_tier(client):
    contract = _start(client)
    state = _resolve_all_choices(client, contract["creation_id"], contract["state"])
    response = client.post(
        f"/api/creations/{contract['creation_id']}/paths/bogus",
        json={"path_id": "warrior", "state_version": state["state_version"]},
    )
    assert response.status_code == 400


def test_pick_path_rejects_when_no_pick_is_pending(client):
    contract = _start(client)
    state = _resolve_all_choices(client, contract["creation_id"], contract["state"])
    # Still level 0: no path pick is pending yet (that unlocks at level 1).
    response = client.post(
        f"/api/creations/{contract['creation_id']}/paths/novice",
        json={"path_id": "warrior", "state_version": state["state_version"]},
    )
    assert response.status_code == 409


def test_pick_path_rejects_unknown_path(client):
    contract = _start(client)
    state = _resolve_all_choices(client, contract["creation_id"], contract["state"])
    state, _ = _advance(client, contract["creation_id"], state)

    response = client.post(
        f"/api/creations/{contract['creation_id']}/paths/novice",
        json={"path_id": "not-a-real-path", "state_version": state["state_version"]},
    )
    assert response.status_code == 400


def test_full_manual_playthrough_level_zero_to_ten_through_expert_and_master(client):
    """Exercise the whole manual wizard: ancestry choices, the Novice pick at
    level 1, the Expert pick at level 3, and a Master pick at level 7,
    reaching level 10 with `can_finalize` true throughout the crossroads."""
    contract = _start(client)
    creation_id = contract["creation_id"]
    state = _resolve_all_choices(client, creation_id, contract["state"])
    assert state["current_level"] == 0

    while state["current_level"] < 10:
        assert state["can_advance"] is True
        assert state["can_finalize"] is True

        awaiting = state["awaiting_path_pick"]
        if awaiting == "novice":
            state, _ = _pick_path(client, creation_id, state, "novice", "warrior")
        elif awaiting == "expert":
            state, _ = _pick_path(client, creation_id, state, "expert", "fighter")
        elif awaiting == "master":
            state, _ = _pick_path(client, creation_id, state, "master", "duelist")
        else:
            state, _ = _advance(client, creation_id, state)

        state = _resolve_all_choices(client, creation_id, state)

    assert state["current_level"] == 10
    assert state["can_advance"] is False
    assert state["can_finalize"] is True

    response = client.post(f"/api/creations/{creation_id}/finalize")
    assert response.status_code == 200
    assert "pdf_url" in response.get_json()


def test_full_manual_playthrough_second_expert_path_at_level_seven(client):
    """At the level 7 crossroads, picking another Expert path instead of a
    Master one must be accepted and must not repeat the first Expert path."""
    contract = _start(client)
    creation_id = contract["creation_id"]
    state = _resolve_all_choices(client, creation_id, contract["state"])

    while state["current_level"] < 7:
        awaiting = state["awaiting_path_pick"]
        if awaiting == "novice":
            state, _ = _pick_path(client, creation_id, state, "novice", "warrior")
        elif awaiting == "expert":
            state, _ = _pick_path(client, creation_id, state, "expert", "fighter")
        else:
            state, _ = _advance(client, creation_id, state)
        state = _resolve_all_choices(client, creation_id, state)

    assert state["awaiting_path_pick"] == "master"

    # Rejects re-picking the same Expert path already chosen at level 3.
    duplicate_response = client.post(
        f"/api/creations/{creation_id}/paths/expert",
        json={"path_id": "fighter", "state_version": state["state_version"]},
    )
    assert duplicate_response.status_code == 400

    state, _ = _pick_path(client, creation_id, state, "expert", "assasin")
    assert state["awaiting_path_pick"] is None


def test_random_mode_reports_every_level_up_to_target_completed(client):
    contract = _start(
        client, mode="random", target_level=3, paths={"novice": "warrior"}
    )
    state = contract["state"]
    assert state["current_level"] == 3
    assert state["completed_steps"] == [0, 1, 2, 3]
    assert state["pending_choices"] == []


def test_random_mode_supports_expert_and_master_paths(client):
    contract = _start(
        client,
        mode="random",
        target_level=10,
        paths={"novice": "warrior", "expert": ["fighter"], "master": "duelist"},
    )
    state = contract["state"]
    assert state["current_level"] == 10
    assert state["completed_steps"] == list(range(11))
    assert state["pending_choices"] == []
