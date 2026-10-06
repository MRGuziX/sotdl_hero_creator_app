import random


def test_rejected_choice_batch_does_not_apply_its_valid_prefix(client):
    random.seed(42)
    initial = client.post("/api/creations", json={"mode": "manual", "ancestry": "human"}).get_json()
    state = initial["state"]
    url = f"/api/creations/{initial['creation_id']}"
    payload = {
        "state_version": state["state_version"],
        "choice_cursor": state["choice_cursor"],
        "selections": [
            state["pending_choices"][0][0],
            {"type": "add_attribute", "name": "health", "value": 9999},
        ],
    }
    for _ in range(3):
        response = client.post(f"{url}/steps/0/choices", json=payload)
        assert response.status_code == 400
        assert client.get(url).get_json() == initial
    response = client.post(f"{url}/rewind_choice", json={"state_version": 0})
    assert response.status_code == 400


def test_successful_batch_records_each_choice_for_undo(client):
    random.seed(42)
    initial = client.post("/api/creations", json={"mode": "manual", "ancestry": "human"}).get_json()
    state = initial["state"]
    url = f"/api/creations/{initial['creation_id']}"
    actions = [group[0] for group in state["level_choices"][:2]]
    response = client.post(
        f"{url}/steps/0/choices",
        json={
            "state_version": 0,
            "choice_cursor": 0,
            "selections": actions,
        },
    )
    assert response.status_code == 200
    updated = response.get_json()["state"]
    assert updated["choice_cursor"] == 2
    restored = client.post(
        f"{url}/rewind_choice",
        json={
            "state_version": updated["state_version"],
        },
    ).get_json()["state"]
    assert restored["choice_cursor"] == 1
    assert restored["hero"]["strength"] == updated["hero"]["strength"]
    assert restored["hero"]["professions"] == state["hero"]["professions"]
