import pytest

from main import app
from models.base_hero import AncestryHero


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def hero():
    return AncestryHero(
        ancestry_name="Człowiek",
        ancestry_id="human",
        strength=10,
        dexterity=10,
        intelligence=10,
        will=10,
        perception=10,
        defense=10,
        health=10,
        healing_rate=1,
        size=[1.0, 1.0],
        speed=10,
    )
