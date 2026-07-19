import os

import pytest

from models.action import AddAttribute, AddItem, AddLanguage, AddProfession, GrantLiteracy
from models.base_hero import AncestryHero
from models.equipment import Weapon
from models.language import Language
from utils.pdf_creator import fill_pdf
from utils.utils import (
    roll_dice,
    get_from_ancestry,
    build_hero,
    add_attribute,
    add_language,
    add_profession,
    add_item,
    add_oddity,
    add_wealth,
    apply_action,
    resolve_choices,
    expand_any_to_choices,
    grant_literacy,
    get_hero,
)


@pytest.fixture
def hero():
    return AncestryHero(
        ancestry_name="Człowiek",
        strength=10,
        dexterity=10,
        intelligence=10,
        will=10,
        perception=10,
        defense=10,
        health=10,
        healing_rate=2,
        size=[1.0, 0.5],
        speed=10,
        languages=[
            Language(name="Wspólny", can_speak=True, can_write=False),
            Language(name="Elficki", can_speak=True, can_write=True),
            Language(name="Krasnoludzki", can_speak=True, can_write=False),
        ],
    )


# --- roll_dice ---

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


# --- add_attribute ---

def test_add_attribute_core(hero):
    add_attribute("strength", 2, hero)
    assert hero.strength == 12


def test_add_attribute_secondary(hero):
    add_attribute("health", 5, hero)
    assert hero.health == 15


def test_add_attribute_any_random(hero):
    add_attribute("any", 1, hero, is_random=True)
    attrs = [hero.strength, hero.dexterity, hero.intelligence, hero.will]
    assert any(a > 10 for a in attrs)


def test_add_attribute_dice_string(hero):
    add_attribute("insanity", "1d6", hero)
    assert 1 <= hero.insanity <= 6


def test_add_attribute_size(hero):
    add_attribute("size", 0.5, hero)
    assert hero.size == [0.5]


# --- add_language ---

def test_add_language_new_speak(hero):
    add_language("Trolli", hero, can_write=False)
    assert any(l.name == "Trolli" and not l.can_write for l in hero.languages)


def test_add_language_grant_write(hero):
    add_language("Wspólny", hero, can_write=True)
    wspólny = next(l for l in hero.languages if l.name == "Wspólny")
    assert wspólny.can_write is True


# --- grant_literacy ---

def test_grant_literacy(hero):
    assert not next(l for l in hero.languages if l.name == "Wspólny").can_write
    grant_literacy("Wspólny", hero)
    assert next(l for l in hero.languages if l.name == "Wspólny").can_write is True


def test_grant_literacy_any(hero):
    grant_literacy("any", hero)
    writable = [l for l in hero.languages if l.can_write]
    assert len(writable) >= 2


# --- add_money ---

def test_add_money_via_action(hero):
    hero.money.okrawki = 10
    assert hero.money.okrawki == 10


def test_add_money_invalid_type(hero):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        hero.money.okrawki = "not_a_number"


# --- add_item ---

def test_add_item_from_store(hero):
    add_item("Oszczep", hero)
    assert len(hero.equipment.weapons) == 1
    assert hero.equipment.weapons[0].name == "Oszczep"


def test_add_item_armor(hero):
    add_item("Miękka skórznia", hero)
    assert len(hero.equipment.armors) == 1


def test_add_item_shield(hero):
    add_item("Duża tarcza", hero)
    assert len(hero.equipment.shields) == 1


def test_add_item_not_found(hero):
    add_item("NonExistentItem", hero)
    assert "nonexistentitem" in hero.equipment.backpack


def test_add_item_with_data(hero):
    action = AddItem(name="Pałka", damage="1k6", grip="Jednoręczny", properties="Finezyjna", item_type="weapon")
    add_item(action.name, hero, item_data=action)
    assert len(hero.equipment.weapons) == 1
    assert hero.equipment.weapons[0].name == "Pałka"


# --- add_profession ---

def test_add_profession_random(hero):
    add_profession("any", hero, is_random=True)
    assert len(hero.professions) > 0


def test_add_profession_specific(hero):
    add_profession("pospolita", hero, is_random=True)
    assert len(hero.professions) == 1


# --- add_oddity ---

def test_add_oddity(hero):
    add_oddity(hero)
    assert hero.oddity != ""


# --- add_wealth ---

def test_add_wealth(hero):
    actions = []
    choices = []
    add_wealth(hero, actions, choices)
    assert hero.wealth != ""


# --- apply_action ---

def test_apply_action_add_attribute(hero):
    action = AddAttribute(name="strength", value=3)
    apply_action(action, hero)
    assert hero.strength == 13


def test_apply_action_add_language(hero):
    action = AddLanguage(name="Trolli", can_write=False)
    apply_action(action, hero)
    assert any(l.name == "Trolli" for l in hero.languages)


def test_apply_action_add_item(hero):
    action = AddItem(name="Oszczep")
    apply_action(action, hero)
    assert len(hero.equipment.weapons) == 1


def test_apply_action_grant_literacy(hero):
    action = GrantLiteracy(target="Wspólny")
    apply_action(action, hero)
    assert next(l for l in hero.languages if l.name == "Wspólny").can_write is True


# --- resolve_choices ---

def test_resolve_choices_random(hero):
    actions = []
    choices = [[AddAttribute(name="strength", value=1), AddAttribute(name="will", value=1)]]
    result = resolve_choices(hero, actions, choices, is_random=True)
    assert len(result) == 1


def test_resolve_choices_manual(hero):
    actions = []
    choices = [[AddAttribute(name="strength", value=1), AddAttribute(name="will", value=1)]]
    selected = [AddAttribute(name="will", value=1)]
    result = resolve_choices(hero, actions, choices, is_random=False, selected_choices=selected)
    assert len(result) == 1
    assert result[0].name == "will"


# --- expand_any_to_choices ---

def test_expand_any_to_choices():
    actions = [
        AddAttribute(name="any", value=1),
        AddProfession(name="any"),
        AddAttribute(name="strength", value=2),
    ]
    choices = []
    remaining, new_choices = expand_any_to_choices(actions, choices)
    assert len(remaining) == 1
    assert remaining[0].name == "strength"
    assert len(new_choices) == 2


# --- get_from_ancestry ---

def test_get_from_ancestry():
    result = get_from_ancestry(roll=1, category="past", ancestry="human")
    assert result is not None
    assert result.description != ""


# --- build_hero ---

def test_build_hero():
    hero, actions, choices = build_hero("human")
    assert hero.ancestry_name == "Człowiek"
    assert hero.backstory != {}
    assert isinstance(actions, list)
    assert isinstance(choices, list)


# --- get_hero ---

def test_get_hero_random():
    hero = get_hero("orc", is_random=True)
    assert hero.ancestry_name == "Ork"
    assert hero.wealth != ""
    assert hero.oddity != ""


def test_get_hero_manual():
    result = get_hero("human", is_random=False)
    if isinstance(result, tuple):
        hero, choices = result
        assert hero.ancestry_name == "Człowiek"
        assert len(choices) > 0
    else:
        assert result.ancestry_name == "Człowiek"


@pytest.mark.parametrize("ancestry", [
    "human", "goblin", "orc", "dwarf", "changeling", "automaton",
])
def test_get_hero_all_ancestries(ancestry):
    hero = get_hero(ancestry, is_random=True)
    assert hero.ancestry_name != ""
    assert hero.wealth != ""


# --- legacy test for dice errors ---

def test_roll_dice_errors():
    from unittest.mock import patch
    with pytest.raises(ArithmeticError):
        with patch('random.randint', return_value=0):
            roll_dice(1, 6)
