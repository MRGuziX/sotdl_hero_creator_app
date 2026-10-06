from domain.state_token import StateTokenCodec
from domain.creation_state import CreationState


def test_carried_tokens_own_nested_input_snapshots_on_encode_and_decode(hero):
    codec = StateTokenCodec("test-secret")
    state = CreationState(hero, creation_inputs={"paths": {"expert": ["fighter"]}})
    token = codec.encode(state)
    state.creation_inputs["paths"]["expert"].append("witch")
    loaded = codec.decode(token)
    assert loaded.creation_inputs["paths"]["expert"] == ["fighter"]
    loaded.touch()
    token = codec.encode(loaded)
    loaded.creation_inputs["paths"]["expert"].clear()
    assert codec.decode(token).creation_inputs["paths"]["expert"] == ["fighter"]
