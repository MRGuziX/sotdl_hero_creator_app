import pytest


@pytest.mark.parametrize("payload", [[], [1], 12, "hello", None])
def test_creation_requires_an_object(client, payload):
    response = client.post("/api/creations", json=payload)
    assert response.status_code == 400
    assert response.is_json


@pytest.mark.parametrize("extra", [
    {"target_level": True},
    {"target_level": 1.5},
    {"paths": {"novice": 123}},
    {"paths": {"novice": "../../hero"}},
    {"paths": {"novice": "cleric_religions"}},
    {"paths": {"expert": "fighter"}},
    {"paths": {"expert": ["fighter", "fighter"]}},
    {"paths": {"novice": "missing"}},
    {"enabled_sources": ["unknown"]},
    {"enabled_sources": ["SWD"]},
])
def test_bad_creation_fields_are_rejected(client, extra):
    response = client.post(
        "/api/creations", json={"mode": "random", "ancestry": "human", **extra}
    )
    assert response.status_code == 400
    assert response.is_json


@pytest.mark.parametrize("suffix,extra", [
    ("advance", {"state_version": True}),
    ("rewind", {"target_level": "1"}),
    ("rewind", {"target_level": -1}),
    ("paths/novice", {"path_id": {}}),
    ("equipment", {"armors": None}),
    ("equipment", {"weapons": [{}]}),
    ("steps/0/choices", {"selections": {}, "choice_cursor": 0}),
    ("steps/0/choices", {"selections": [], "choice_cursor": True}),
])
def test_invalid_mutations_leave_creation_unchanged(client, suffix, extra):
    initial = client.post(
        "/api/creations", json={"mode": "manual", "ancestry": "human"}
    ).get_json()
    url = f"/api/creations/{initial['creation_id']}"
    response = client.post(
        f"{url}/{suffix}", json={"state_version": initial["state"]["state_version"], **extra}
    )
    assert response.status_code == 400
    assert response.is_json
    assert client.get(url).get_json() == initial
