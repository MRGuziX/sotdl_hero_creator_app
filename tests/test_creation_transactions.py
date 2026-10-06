from domain.creation_state import CreationState
from domain.state_token import StateTokenCodec


def test_decoded_snapshots_are_independent(hero):
    codec = StateTokenCodec("test-secret")
    initial = CreationState(hero, creation_inputs={"paths": {"expert": []}})
    token = codec.encode(initial)
    read = codec.decode(token)
    read.hero.health += 99
    read.creation_inputs["paths"]["expert"].append("fighter")
    assert codec.decode(token).to_dict() == initial.to_dict()


def test_starting_another_character_does_not_replace_the_first(client):
    first = client.post("/api/creations", json={"mode": "manual", "ancestry": "human"}).get_json()
    second = client.post("/api/creations", json={"mode": "manual", "ancestry": "dwarf"}).get_json()
    assert first["creation_id"] != second["creation_id"]
    assert client.resume(f"/api/creations/{first['creation_id']}").status_code == 200
    assert client.resume(f"/api/creations/{second['creation_id']}").status_code == 200
