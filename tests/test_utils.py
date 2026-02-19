import pytest

from utils.utils import (
    roll_dice,
    get_from_ancestry,
    build_hero,
    change_choices_to_actions,
    add_profession,
    add_language,
    add_attribute,
    bulk_update_attributes,
    add_wealth,
    add_money,
    add_weapon,
    add_shield,
    add_armor,
    add_oddity,
    get_hero,
)


@pytest.fixture
def character_data():
    return {
        "actions": [],
        "backstory": {
            "age": "Dorosły w średnim wieku, 36–55 lat.",
            "appearance": "Posiadasz kilka cech fizycznych, które dodają ci atrakcyjności.",
            "body": "Jesteś średniego wzrostu i wagi.",
            "personality": "Ponad wszystkim innym stawiasz dobro swoje i swoich bliskich.",
            "past": "Zakochałeś się; związek ten nadal trwa lub zakończył się dobrze.",
            "religion": "Jesteś wyznawcą Nowego Boga."
        },
        "choices": [],
        "general": {
            "ancestry_name": "Człowiek",
            "corruption": 0,
            "damage": 0,
            "defense": 10,
            "dexterity": 11,
            "healing_rate": 2,
            "health": 10,
            "insanity": 0,
            "intelligence": 10,
            "language": [
                {
                    "known": False,
                    "name": "Wspólny"
                },
                {
                    "known": True,
                    "name": "Elficki"
                },
                {
                    "known": False,
                    "name": "Krasnoludzki"
                },
            ],
            "perception": 10,
            "power": 0,
            "size": [
                1.0,
                0.5
            ],
            "speed": 10,
            "strength": 10,
            "will": 10
        },
        "professions": [],
        "spells": [],
        "wealth": "",
        "money": [
            {
                "okrawki": 0
            },
            {
                "miedziaki": 0
            },
            {
                "srebrniki": 0
            },
            {
                "złote korony": 0
            }
        ],
        "oddity": "",
        "equipment": [
            {
                "weapons": []
            },
            {
                "shields": []
            },
            {
                "armors": []
            },
            {
                "backpack": []
            }
        ],
        "talents": []
    }

# Tests for roll_dice
def test_roll_dice_valid():
    result = roll_dice(3, 6)
    assert 3 <= result <= 18

def test_roll_dice_invalid_type():
    with pytest.raises(TypeError):
        roll_dice("3", 6)
    with pytest.raises(TypeError):
        roll_dice(3, "6")

def test_roll_dice_invalid_value():
    with pytest.raises(ValueError):
        roll_dice(0, 6)
    with pytest.raises(ValueError):
        roll_dice(3, 0)

# Tests for add_money
def test_add_money_okrawki(character_data):
    add_money(10, "okrawki", character_data)
    assert character_data["money"][0]["okrawki"] == 10

def test_add_money_miedziaki(character_data):
    add_money(5, "miedziaki", character_data)
    assert character_data["money"][1]["miedziaki"] == 5

def test_add_money_invalid_type(character_data):
    with pytest.raises(ValueError):
        add_money(10, "dollars", character_data)

# Tests for add_language
def test_add_language_new_speak(character_data):
    # Try adding a language not in list.
    # In utils.py: elif not known and language_type not in possible_languages_to_learn:
    # "Trolli" is in languages_list but not in character_data["general"]["language"], 
    # so it IS in possible_languages_to_learn.
    # To trigger the append, we need a language NOT in possible_languages_to_learn.
    add_language("CustomLanguage", character_data, known=False)
    assert any(lang["name"] == "CustomLanguage" and lang["known"] is False for lang in character_data["general"]["language"])

def test_add_language_new_write(character_data):
    # Elficki is known (True) in fixture. Wspólny is NOT known (False).
    # Learn to write Wspólny.
    add_language("Wspólny", character_data, known=True)
    assert any(lang["name"] == "Wspólny" and lang["known"] is True for lang in character_data["general"]["language"])

# Tests for add_attribute
def test_add_attribute_core(character_data):
    initial_strength = character_data["general"]["strength"]
    add_attribute("strength", 2, character_data)
    assert character_data["general"]["strength"] == initial_strength + 2

def test_add_attribute_any_random(character_data):
    add_attribute("any", 1, character_data, is_random=True)
    # Check if one of core attributes increased
    attrs = ["strength", "dexterity", "intelligence", "will"]
    assert any(character_data["general"][attr] > 10 for attr in attrs)

# Tests for add_profession
def test_add_profession_random(character_data):
    add_profession("any", character_data, is_random=True)
    assert len(character_data["professions"]) > 0

# Tests for equipment (these depend on data_base/equipment/equ.json)
def test_add_weapon(character_data):
    # Based on equ.json content, assuming 'Oszczep' exists
    add_weapon("Oszczep", character_data)
    assert len(character_data["equipment"][0]["weapons"]) == 1
    assert character_data["equipment"][0]["weapons"][0]["name"].lower() == "oszczep"

def test_add_armor(character_data):
    # Assuming 'Miękka skórznia' exists
    add_armor("Miękka skórznia", character_data)
    assert len(character_data["equipment"][2]["armors"]) == 1
    assert character_data["equipment"][2]["armors"][0]["name"].lower() == "miękka skórznia"

def test_add_shield(character_data):
    # Assuming 'Mała tarcza' or similar exists
    # I see 'Duża tarcza' in old tests
    add_shield("Duża tarcza", character_data)
    assert len(character_data["equipment"][1]["shields"]) == 1
    assert character_data["equipment"][1]["shields"][0]["name"].lower() == "duża tarcza"

# Tests for add_oddity
def test_add_oddity(character_data):
    add_oddity(character_data)
    assert character_data["oddity"] != ""

# Tests for add_wealth
def test_add_wealth(character_data):
    add_wealth(character_data)
    assert character_data["wealth"] != ""

# Tests for change_choices_to_actions
def test_change_choices_to_actions(character_data):
    character_data["choices"] = [[{"strength": 1}, {"dexterity": 1}]]
    change_choices_to_actions(character_data, is_random=True)
    assert len(character_data["actions"]) == 1
    assert "add_attribute" in character_data["actions"][0]

# Tests for bulk_update_attributes
def test_bulk_update_attributes(character_data):
    character_data["actions"] = [{"add_attribute": {"strength": 2}}]
    bulk_update_attributes(character_data)
    assert character_data["general"]["strength"] == 12

# Tests for get_from_ancestry
def test_get_from_ancestry():
    # This reads from filesystem, testing with 'human' and 'past'
    result = get_from_ancestry(roll=1, category="past", ancestry="human")
    assert result is not None
    # result can be a tuple (description, action) or just description

# High level tests
def test_build_hero():
    hero = build_hero("human")
    assert hero["general"]["ancestry_name"] == "Człowiek"
    assert hero["backstory"] != {}

def test_get_hero():
    hero = get_hero("orc")
    assert hero["general"]["ancestry_name"] == "Ork"
    assert hero["wealth"] != ""