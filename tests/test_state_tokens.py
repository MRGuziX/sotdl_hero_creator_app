from concurrent.futures import ThreadPoolExecutor

import pytest

from domain.creation_service import CreationError, mutate_creation
from domain.creation_state import CreationState, CreationStateError
from domain.state_token import MAX_TOKEN_LENGTH, StateTokenCodec, StateTokenSizeError


def test_tokens_continue_on_an_independent_instance_with_all_history(hero):
    first = StateTokenCodec("test-secret")
    second = StateTokenCodec("test-secret")
    state = CreationState(hero, creation_inputs={"paths": {"expert": []}})
    state.checkpoint("level")
    token = first.encode(state)
    restored = second.decode(token)
    assert restored.to_dict() == state.to_dict()
    restored.hero.health += 5
    restored.creation_inputs["paths"]["expert"].append("fighter")
    assert second.decode(token).to_dict() == state.to_dict()


def test_modified_or_wrong_secret_tokens_are_rejected(hero):
    codec = StateTokenCodec("test-secret")
    token = codec.encode(CreationState(hero))
    payload, signature = token.rsplit(".", 1)
    modified = payload + "." + ("a" if signature[0] != "a" else "b") + signature[1:]
    for invalid in [modified, "nonsense", "", None, "a" * (MAX_TOKEN_LENGTH + 1)]:
        with pytest.raises(CreationStateError):
            codec.decode(invalid)
    with pytest.raises(CreationStateError):
        StateTokenCodec("another-secret").decode(token)


def test_incompatible_or_malformed_signed_states_are_rejected(hero):
    codec = StateTokenCodec("test-secret")
    payload = CreationState(hero).to_dict()
    payload["version"] = -1
    with pytest.raises(CreationStateError):
        codec.decode(codec.serializer.dumps(payload))
    for payload in [None, [], {"version": 4}]:
        with pytest.raises(CreationStateError):
            codec.decode(codec.serializer.dumps(payload))


def test_failed_stateless_mutation_preserves_original_snapshot(hero):
    initial = CreationState(hero, creation_inputs={"paths": {"expert": []}})
    initial.checkpoint("level")
    before = initial.to_dict()

    def reject(state):
        state.hero.health += 99
        state.creation_inputs["paths"]["expert"].append("fighter")
        state.checkpoint("choice")
        raise CreationError("Rejected")

    with pytest.raises(CreationError, match="Rejected"):
        mutate_creation(initial, 0, reject)
    assert initial.to_dict() == before
    with pytest.raises(CreationError, match="Stale state"):
        mutate_creation(initial, 3, reject)


def test_parallel_requests_branch_without_mutating_the_carried_snapshot(hero):
    initial = CreationState(hero)
    before = initial.to_dict()

    def execute(_):
        return mutate_creation(initial, 0, lambda state: setattr(state.hero, "health", 20))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(execute, range(2)))
    assert all(state.hero.health == 20 and state.state_version == 1 for state in results)
    assert initial.to_dict() == before


@pytest.mark.parametrize("limit", ["MAX_STATE_BYTES", "MAX_TOKEN_LENGTH"])
def test_oversized_generated_capsules_have_a_distinct_recoverable_error(hero, monkeypatch, limit):
    monkeypatch.setattr("domain.state_token." + limit, 1)
    with pytest.raises(StateTokenSizeError):
        StateTokenCodec("test-secret").encode(CreationState(hero))
