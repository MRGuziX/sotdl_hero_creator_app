from data.creations import MemoryCreationRepository
from domain.creation_state import CreationState


def test_repository_owns_nested_input_snapshots_on_create_and_save(hero):
    repository = MemoryCreationRepository()
    state = CreationState(hero, creation_inputs={"paths": {"expert": ["fighter"]}})
    repository.create("owner", state)
    state.creation_inputs["paths"]["expert"].append("witch")
    loaded = repository.get("owner", state.state_id)
    assert loaded.creation_inputs["paths"]["expert"] == ["fighter"]
    loaded.touch()
    assert repository.save("owner", loaded, 0)
    loaded.creation_inputs["paths"]["expert"].clear()
    assert repository.get("owner", state.state_id).creation_inputs["paths"]["expert"] == ["fighter"]
