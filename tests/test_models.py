import json

import pytest
from pydantic import ValidationError

from models.action import (
    Action,
    AddAttribute,
    AddItem,
    AddLanguage,
    AddProfession,
    GrantLiteracy,
)
from models.ancestry import AncestryData
from models.base_hero import AncestryHero
from models.equipment import Armor, Equipment, Money, Shield, Weapon
from models.language import Language
from models.spell import Spell, Tradition
from models.tables import ProfessionEntry, RollTableEntry, WealthEntry
from models.talent import Talent


class TestLanguage:
    def test_defaults(self):
        lang = Language(name="Wspólny")
        assert lang.can_speak is True
        assert lang.can_write is False

    def test_full(self):
        lang = Language(name="Elficki", can_speak=True, can_write=True)
        assert lang.can_write is True


class TestTalent:
    def test_defaults(self):
        t = Talent(name="Test", description="Desc")
        assert t.level == 0

    def test_with_level(self):
        t = Talent(name="Test", description="Desc", level=4)
        assert t.level == 4


class TestMoney:
    def test_defaults(self):
        m = Money()
        assert m.okrawki == 0
        assert m.zlote_korony == 0

    def test_mutation(self):
        m = Money()
        m.okrawki = 5
        assert m.okrawki == 5

    def test_validates_type(self):
        with pytest.raises(ValidationError):
            Money(okrawki="not_a_number")


class TestEquipment:
    def test_defaults(self):
        e = Equipment()
        assert e.weapons == []
        assert e.backpack == []

    def test_add_weapon(self):
        e = Equipment()
        w = Weapon(name="Miecz", damage="1k6", grip="Jednoręczny")
        e.weapons.append(w)
        assert len(e.weapons) == 1
        assert e.weapons[0].name == "Miecz"

    def test_add_shield(self):
        e = Equipment()
        s = Shield(name="Tarcza", damage="1", grip="Chwyt dowolny")
        e.shields.append(s)
        assert len(e.shields) == 1

    def test_add_armor(self):
        e = Equipment()
        a = Armor(name="Kolczuga", defence="15")
        e.armors.append(a)
        assert len(e.armors) == 1


class TestSpell:
    def test_creation(self):
        s = Spell(name="Fireball", description="Boom", level=1)
        assert s.level == 1

    def test_default_level(self):
        s = Spell(name="Light", description="Glow")
        assert s.level == 0


class TestActionDiscriminator:
    def test_add_attribute(self):
        data = {"type": "add_attribute", "name": "strength", "value": 2}
        from pydantic import TypeAdapter
        adapter = TypeAdapter(Action)
        action = adapter.validate_python(data)
        assert isinstance(action, AddAttribute)
        assert action.name == "strength"
        assert action.value == 2

    def test_add_profession(self):
        data = {"type": "add_profession", "name": "any"}
        from pydantic import TypeAdapter
        adapter = TypeAdapter(Action)
        action = adapter.validate_python(data)
        assert isinstance(action, AddProfession)

    def test_add_language(self):
        data = {"type": "add_language", "name": "Elficki", "can_write": True}
        from pydantic import TypeAdapter
        adapter = TypeAdapter(Action)
        action = adapter.validate_python(data)
        assert isinstance(action, AddLanguage)
        assert action.can_write is True

    def test_add_item(self):
        data = {"type": "add_item", "name": "Miecz"}
        from pydantic import TypeAdapter
        adapter = TypeAdapter(Action)
        action = adapter.validate_python(data)
        assert isinstance(action, AddItem)

    def test_grant_literacy(self):
        data = {"type": "grant_literacy", "target": "any"}
        from pydantic import TypeAdapter
        adapter = TypeAdapter(Action)
        action = adapter.validate_python(data)
        assert isinstance(action, GrantLiteracy)

    def test_add_attribute_with_dice_string(self):
        data = {"type": "add_attribute", "name": "insanity", "value": "1d6"}
        from pydantic import TypeAdapter
        adapter = TypeAdapter(Action)
        action = adapter.validate_python(data)
        assert isinstance(action, AddAttribute)
        assert action.value == "1d6"

    def test_add_attribute_with_float(self):
        data = {"type": "add_attribute", "name": "size", "value": 0.5}
        from pydantic import TypeAdapter
        adapter = TypeAdapter(Action)
        action = adapter.validate_python(data)
        assert isinstance(action, AddAttribute)
        assert action.value == 0.5


class TestAncestryHero:
    def test_creation(self):
        hero = AncestryHero(
            ancestry_name="Test",
            strength=10, dexterity=10, intelligence=10, will=10,
            perception=10, defense=10, health=10, healing_rate=2,
            size=[1.0], speed=10,
        )
        assert hero.ancestry_name == "Test"
        assert hero.level == 0

    def test_mutation(self):
        hero = AncestryHero(
            ancestry_name="Test",
            strength=10, dexterity=10, intelligence=10, will=10,
            perception=10, defense=10, health=10, healing_rate=2,
            size=[1.0], speed=10,
        )
        hero.strength += 2
        assert hero.strength == 12

    def test_validates_on_mutation(self):
        hero = AncestryHero(
            ancestry_name="Test",
            strength=10, dexterity=10, intelligence=10, will=10,
            perception=10, defense=10, health=10, healing_rate=2,
            size=[1.0], speed=10,
        )
        with pytest.raises(ValidationError):
            hero.strength = "not_a_number"


class TestAncestryData:
    @pytest.mark.parametrize("ancestry", [
        "human", "goblin", "orc", "dwarf", "changeling", "automaton",
    ])
    def test_load_ancestry_json(self, ancestry):
        with open(f"data_base/ancestry/{ancestry}/{ancestry}.json") as f:
            data = json.load(f)
        result = AncestryData.model_validate(data)
        assert result.general.ancestry_name != ""


class TestTableModels:
    def test_roll_table_entry(self):
        entry = RollTableEntry(roll=[1, 2], description="Test entry")
        assert entry.actions == []
        assert entry.choices == []

    def test_profession_entry(self):
        entry = ProfessionEntry(roll=[1], description="Scholar")
        assert entry.action is None

    def test_profession_entry_with_action(self):
        entry = ProfessionEntry(
            roll=[1, 2],
            description="Czciciel",
            action=GrantLiteracy(target="any"),
        )
        assert isinstance(entry.action, GrantLiteracy)

    def test_wealth_entry(self):
        entry = WealthEntry(roll=[3, 4], description="Poverty")
        assert entry.backpack == ""
        assert entry.money is None
