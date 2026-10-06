from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from data.creations import MemoryCreationRepository
from domain.creation_service import CreationError, CreationService
from domain.creation_state import CreationState


def test_concurrent_versions_commit_only_once(hero):
    repository = MemoryCreationRepository()
    initial = CreationState(hero=hero, creation_inputs={"paths": {"expert": []}})
    repository.create("owner", initial)
    barrier = Barrier(2)

    def operation(state):
        barrier.wait(timeout=5)
        state.hero.health += 1
        state.creation_inputs["paths"]["expert"].append("fighter")

    def execute():
        try:
            return CreationService(repository).mutate("owner", initial.state_id, 0, operation)
        except CreationError as error:
            return error.status

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: execute(), range(2)))
    assert sum(isinstance(result, CreationState) for result in results) == 1
    assert results.count(409) == 1
    stored = repository.get("owner", initial.state_id)
    assert stored.hero.health == initial.hero.health + 1
    assert stored.state_version == 1
    assert stored.creation_inputs["paths"]["expert"] == ["fighter"]


def test_exception_rolls_back_all_fields_and_history(hero):
    repository = MemoryCreationRepository()
    initial = CreationState(hero=hero, creation_inputs={"paths": {"expert": []}})
    initial.checkpoint("level")
    repository.create("owner", initial)

    def operation(state):
        state.checkpoint("choice")
        state.hero.health += 99
        state.creation_inputs["paths"]["expert"].append("fighter")
        raise CreationError("Rejected")

    with pytest.raises(CreationError, match="Rejected"):
        CreationService(repository).mutate("owner", initial.state_id, 0, operation)
    assert repository.get("owner", initial.state_id).to_dict() == initial.to_dict()


def test_reads_are_isolated_and_owned(hero):
    repository = MemoryCreationRepository()
    initial = CreationState(hero=hero, creation_inputs={"paths": {"expert": []}})
    repository.create("owner", initial)
    read = repository.get("owner", initial.state_id)
    read.hero.health += 99
    read.creation_inputs["paths"]["expert"].append("fighter")
    assert repository.get("owner", initial.state_id).to_dict() == initial.to_dict()
    assert repository.get("another-owner", initial.state_id) is None
    assert repository.list("another-owner") == []
    assert repository.save("another-owner", read, 0) is False


def test_starting_another_character_does_not_replace_the_first(client):
    first = client.post("/api/creations", json={"mode": "manual", "ancestry": "human"}).get_json()
    second = client.post("/api/creations", json={"mode": "manual", "ancestry": "dwarf"}).get_json()
    assert first["creation_id"] != second["creation_id"]
    assert client.get(f"/api/creations/{first['creation_id']}").status_code == 200
    assert client.get(f"/api/creations/{second['creation_id']}").status_code == 200
