import random

import pytest


def start(client):
    random.seed(42)
    return client.post("/api/creations", json={"mode": "manual", "ancestry": "human"}).get_json()


def post(client, contract, operation, **extra):
    response = client.post(
        f"/api/creations/{contract['creation_id']}/{operation}",
        json={"state_version": contract["state"]["state_version"], **extra},
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def choose(client, contract, action=None):
    state = contract["state"]
    return post(
        client,
        contract,
        f"steps/{state['current_level']}/choices",
        selections=[action or state["pending_choices"][0][0]],
        choice_cursor=state["choice_cursor"],
    )


def complete(client, contract):
    for _ in range(150):
        if not contract["state"]["pending_choices"]:
            return contract
        contract = choose(client, contract)
    raise AssertionError("Creation choices did not terminate")


def test_choice_undo_restores_exact_previous_character_without_randomness(client, monkeypatch):
    before = choose(client, start(client))
    after = choose(client, before)
    monkeypatch.setattr(random, "randint", lambda *args: pytest.fail("Undo must not roll dice"))
    restored = post(client, after, "rewind_choice")
    assert restored["state"]["hero"] == before["state"]["hero"]
    assert restored["state"]["choice_cursor"] == before["state"]["choice_cursor"]
    assert restored["state"]["selections"] == before["state"]["selections"]
    assert restored["state"]["state_version"] == after["state"]["state_version"] + 1


@pytest.mark.parametrize("target", [0, 1, 3, 7])
def test_level_undo_restores_entry_snapshot_and_reopens_paths(client, monkeypatch, target):
    contract = start(client)
    entries = {0: contract["state"]}
    while contract["state"]["current_level"] <= target:
        contract = complete(client, contract)
        state = contract["state"]
        tier = state["awaiting_path_pick"]
        if tier:
            path = {"novice": "warrior", "expert": "fighter", "master": "duelist"}[tier]
            contract = post(client, contract, f"paths/{tier}", path_id=path)
            continue
        if state.get("awaiting_equipment_pick"):
            contract = post(client, contract, "equipment")
            continue
        contract = post(client, contract, "advance")
        entries[contract["state"]["current_level"]] = contract["state"]
    monkeypatch.setattr(random, "randint", lambda *args: pytest.fail("Undo must not roll dice"))
    restored = post(client, contract, "rewind", target_level=target)
    assert restored["state"]["hero"] == entries[target]["hero"]
    assert restored["state"]["paths"] == entries[target]["paths"]
    assert restored["state"]["awaiting_path_pick"] == entries[target]["awaiting_path_pick"]
    assert restored["state"]["hero"]["level"] == target
    assert restored["state"]["state_version"] > contract["state"]["state_version"]
    repeated = post(client, restored, "rewind", target_level=target)
    assert repeated["state"]["hero"] == restored["state"]["hero"]


def test_spell_undo_restores_dynamic_spell_choices(client):
    contract = post(client, complete(client, start(client)), "advance")
    contract = post(client, contract, "paths/novice", path_id="mage")
    while contract["state"]["pending_choices"][0][0]["type"] != "add_tradition":
        contract = choose(client, contract)
    tradition = next(
        action
        for action in contract["state"]["pending_choices"][0]
        if action["name"] == "Tradycja Ognia"
    )
    before = choose(client, contract, tradition)
    assert before["state"]["pending_choices"][0][0]["type"] == "add_spell"
    after = choose(client, before)
    restored = post(client, after, "rewind_choice")
    assert restored["state"]["hero"] == before["state"]["hero"]
    assert restored["state"]["pending_choices"] == before["state"]["pending_choices"]


@pytest.mark.parametrize("level,tier", [(1, "novice"), (3, "expert"), (7, "master")])
def test_cancel_path_pick_returns_to_completed_previous_level(client, monkeypatch, level, tier):
    contract = start(client)
    while contract["state"]["current_level"] < level:
        contract = complete(client, contract)
        state = contract["state"]
        if state["awaiting_path_pick"]:
            path_tier = state["awaiting_path_pick"]
            path = {"novice": "warrior", "expert": "fighter"}[path_tier]
            contract = post(client, contract, f"paths/{path_tier}", path_id=path)
            continue
        if state["awaiting_equipment_pick"]:
            contract = post(client, contract, "equipment")
            continue
        previous = contract
        contract = post(client, contract, "advance")
    pending = complete(client, contract)
    assert pending["state"]["awaiting_path_pick"] == tier
    monkeypatch.setattr(random, "randint", lambda *args: pytest.fail("Back must not reroll"))

    for _ in range(2):
        restored = post(client, pending, "cancel_advance")
        state = restored["state"]
        assert state["current_level"] == level - 1
        assert state["hero"] == previous["state"]["hero"]
        assert state["paths"] == previous["state"]["paths"]
        assert state["selections"] == previous["state"]["selections"]
        assert state["pending_choices"] == []
        assert state["can_advance"] and state["can_finalize"]
        assert state["awaiting_path_pick"] is None
        assert state["invalidated_levels"] == list(range(level, 11))
        assert state["state_version"] == pending["state"]["state_version"] + 1
        resumed = client.resume(f"/api/creations/{restored['creation_id']}")
        assert resumed.json == restored

        pending = complete(client, post(client, restored, "advance"))
        assert pending["state"]["awaiting_path_pick"] == tier
        assert pending["state"]["hero"] == contract["state"]["hero"]


@pytest.mark.parametrize("mode", ["manual", "random"])
def test_cancel_advance_is_rejected_outside_an_active_path_pick(client, mode):
    contract = client.post("/api/creations", json={"mode": mode, "ancestry": "human"}).json
    response = client.post(
        f"/api/creations/{contract['creation_id']}/cancel_advance",
        json={"state_version": contract["state"]["state_version"]},
    )
    assert response.status_code == 409
    assert client.resume(f"/api/creations/{contract['creation_id']}").json == contract


def test_cancel_advance_rejects_a_stale_version_and_keeps_the_path_pick(client):
    pending = post(client, complete(client, start(client)), "advance")
    response = client.post(
        f"/api/creations/{pending['creation_id']}/cancel_advance",
        json={"state_version": pending["state"]["state_version"] - 1},
    )
    assert response.status_code == 409
    assert client.resume(f"/api/creations/{pending['creation_id']}").json == pending


def test_legacy_path_pick_can_go_back_without_an_advance_checkpoint(client):
    from domain.state_token import StateTokenCodec
    from main import app

    initial = start(client)
    pending = post(client, complete(client, initial), "advance")
    codec = StateTokenCodec(app.secret_key)
    state = codec.decode(pending["state_token"])
    state.checkpoints = [item for item in state.checkpoints if item["kind"] != "advance"]
    response = client.post(
        f"/api/creations/{pending['creation_id']}/cancel_advance",
        json={"state_token": codec.encode(state), "state_version": state.state_version},
    )
    assert response.status_code == 200
    restored = response.json["state"]
    assert restored["current_level"] == 0
    assert restored["hero"] == initial["state"]["hero"]
    assert restored["pending_choices"] == initial["state"]["pending_choices"]
