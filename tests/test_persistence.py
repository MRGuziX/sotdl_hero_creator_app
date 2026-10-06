import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest

from data.persistence import SQLiteCreationRepository, PostgresCreationRepository
from domain.creation_state import CreationState, CreationStateError


@pytest.fixture(params=["sqlite", "postgres"])
def repositories(request, tmp_path):
    if request.param == "sqlite":

        def factory():
            return SQLiteCreationRepository(tmp_path / "creations.db")
    else:
        url = os.environ.get("TEST_DATABASE_URL")
        if not url:
            pytest.skip("Set TEST_DATABASE_URL to run actual PostgreSQL integration tests")

        def factory():
            return PostgresCreationRepository(url)

        factory().initialize()
    return factory(), factory()


def test_restart_ownership_and_independent_reads(repositories, hero):
    first, restarted = repositories
    owner = uuid4().hex
    state = CreationState(hero)
    state.checkpoint("level")
    first.create(owner, state)
    loaded = restarted.get(owner, state.state_id)
    assert loaded.to_dict() == state.to_dict()
    loaded.hero.health += 20
    assert restarted.get(owner, state.state_id).hero.health == state.hero.health
    assert restarted.get("someone-else", state.state_id) is None
    assert restarted.list("someone-else") == []
    assert [item.state_id for item in restarted.list(owner)] == [state.state_id]


def test_compare_and_swap_across_connections(repositories, hero):
    first, second = repositories
    owner = uuid4().hex
    state = CreationState(hero)
    first.create(owner, state)
    barrier = Barrier(2)

    def attempt(repository):
        working = repository.get(owner, state.state_id)
        working.touch()
        barrier.wait()
        return repository.save(owner, working, 0)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, [first, second]))
    assert sorted(results) == [False, True]
    assert first.get(owner, state.state_id).state_version == 1


def test_immutable_exports_survive_restart_and_later_mutations(repositories, hero):
    first, second = repositories
    owner = uuid4().hex
    state = CreationState(hero)
    first.create(owner, state)
    assert first.pin_export(owner, state)
    original = state.hero.model_dump(mode="json")
    state.hero.health += 20
    state.touch()
    assert second.save(owner, state, 0)
    assert second.pin_export(owner, state)
    assert first.get_export(owner, state.state_id, 0) == original
    assert first.get_export(owner, state.state_id, 1) == state.hero.model_dump(mode="json")
    assert second.get_export("someone-else", state.state_id, 0) is None
    assert not first.pin_export("someone-else", state)


def test_expiry_and_incompatible_schema(repositories, hero):
    first, second = repositories
    owner = uuid4().hex
    state = CreationState(hero)
    state.version = -1
    first.create(owner, state)
    with pytest.raises(CreationStateError):
        second.get(owner, state.state_id)
    second.clock = lambda: first.clock() + first.ttl + 1
    assert second.get(owner, state.state_id) is None
    assert second.save(owner, state, 0) is False


def test_listing_is_session_owned(client):
    started = client.post("/api/creations", json={"mode": "random", "ancestry": "human"}).json
    response = client.get("/api/creations")
    assert response.json["creations"][0]["state_id"] == started["state"]["state_id"]
