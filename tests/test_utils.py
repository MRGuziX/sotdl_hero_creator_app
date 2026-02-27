import os

import pytest

from utils.pdf_creator import fill_pdf
from utils.utils import (
    roll_dice,
    get_from_ancestry,
    build_hero,
    change_choices_to_actions,
    add_profession,
    add_language,
    add_entry,
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
        "backstory": {
            "age": "Dorosły w średnim wieku, 36–55 lat.",
            "appearance": "Posiadasz kilka cech fizycznych, które dodają ci atrakcyjności.",
            "body": "Jesteś średniego wzrostu i wagi.",
            "personality": "Ponad wszystkim innym stawiasz dobro swoje i swoich bliskich.",
            "past": "Zakochałeś się; związek ten nadal trwa lub zakończył się dobrze.",
            "religion": "Jesteś wyznawcą Nowego Boga."
        },
        "general": {
            "ancestry_name": "Człowiek",
            "corruption": 0,
            "damage": 0,
            "defense": 10,
            "dexterity": 10,
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
        "talents": [],
        "actions": [
            {
                "add_attribute": {
                    "name": "intelligence",
                    "value": 5
                }
            },
            {
                "add_profession": {
                    "name": "any"
                }
            },
            {
                "add_profession": {
                    "name": "naukowa"
                }
            },
            {
                "add_language": {
                    "name": "Wspólny",
                    "known": False
                }
            }
        ],
        "choices": [
            [
                {
                    "language": {
                        "known": False,
                        "name": "any"
                    }
                },
                {
                    "profession": "any"
                }
            ]
        ]
    }


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


def test_add_money_okrawki(character_data):
    add_money(10, "okrawki", character_data)
    assert character_data["money"][0]["okrawki"] == 10


def test_add_money_miedziaki(character_data):
    add_money(5, "miedziaki", character_data)
    assert character_data["money"][1]["miedziaki"] == 5


def test_add_money_invalid_type(character_data):
    with pytest.raises(ValueError):
        add_money(10, "dollars", character_data)


def test_add_language_new_speak(character_data):
    add_language("CustomLanguage", character_data, known=False)
    assert any(
        lang["name"] == "CustomLanguage" and lang["known"] is False for lang in character_data["general"]["language"])


def test_add_language_new_write(character_data):
    add_language("Wspólny", character_data, known=True)
    assert any(lang["name"] == "Wspólny" and lang["known"] is True for lang in character_data["general"]["language"])


def test_add_attribute_core(character_data):
    initial_strength = character_data["general"]["strength"]
    add_entry("strength", 2, character_data)
    assert character_data["general"]["strength"] == initial_strength + 2


def test_add_attribute_any_random(character_data):
    add_entry("any", 1, character_data, is_random=True)
    attrs = ["strength", "dexterity", "intelligence", "will"]
    assert any(character_data["general"][attr] > 10 for attr in attrs)


# Tests for add_profession
def test_add_profession_random(character_data):
    add_profession("any", character_data, is_random=True)
    assert len(character_data["professions"]) > 0


def test_add_weapon(character_data):
    add_weapon("Oszczep", character_data)
    assert len(character_data["equipment"][0]["weapons"]) == 1
    assert character_data["equipment"][0]["weapons"][0]["name"].lower() == "oszczep"


def test_add_armor(character_data):
    add_armor("Miękka skórznia", character_data)
    assert len(character_data["equipment"][2]["armors"]) == 1
    assert character_data["equipment"][2]["armors"][0]["name"].lower() == "miękka skórznia"


def test_add_shield(character_data):
    add_shield("Duża tarcza", character_data)
    assert len(character_data["equipment"][1]["shields"]) == 1
    assert character_data["equipment"][1]["shields"][0]["name"].lower() == "duża tarcza"


def test_add_oddity(character_data):
    add_oddity(character_data)
    assert character_data["oddity"] != ""


def test_add_wealth(character_data):
    add_wealth(character_data)
    assert character_data["wealth"] != ""


def test_bulk_update_attributes(character_data):
    character_data["actions"] = [{"add_attribute": {"strength": 2}}]
    bulk_update_attributes(character_data)
    assert character_data["general"]["strength"] == 12


def test_get_from_ancestry():
    result = get_from_ancestry(roll=1, category="past", ancestry="human")
    assert result is not None


def test_build_hero():
    hero = build_hero("human")
    assert hero["general"]["ancestry_name"] == "Człowiek"
    assert hero["backstory"] != {}


def test_get_hero():
    hero = get_hero("orc")
    assert hero["general"]["ancestry_name"] == "Ork"
    assert hero["wealth"] != ""


def test_create_hero():
    hero = get_hero("orc")
    output_dir = os.path.join(os.getcwd(), "output")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    output_path = os.path.join(output_dir, "test_hero.pdf")
    fill_pdf(hero, output_path)
    assert os.path.exists(output_path)


def test_choices_to_actions(character_data):
    change_choices_to_actions(character_data=character_data)
    print(character_data)


def test_bulk_actions(character_data):
    bulk_update_attributes(character_data=character_data, is_random=True)

    print(character_data)


def test_add_entry(character_data):
    actions = [
        {
            "add_attribute": {
                "name": "any",
                "value": 1
            }
        },
        {
            "add_profession": {
                "name": "any"
            }
        },
        {
            "add_profession": {
                "name": "naukowa"
            }
        },
        {
            "add_language": {
                "name": "Wspólny",
                "known": False
            }
        }
    ]
    for action in actions:
        add_entry(entry=action, character_data=character_data)
    print(character_data)
