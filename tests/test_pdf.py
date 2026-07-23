import json
import os
import tempfile

import pytest
from pypdf import PdfReader

from models.base_hero import AncestryHero
from models.language import Language
from models.spell import Spell
from models.talent import Talent
from utils.pdf_creator import (
    _spell_description_bounds,
    _spell_description_font_size,
    _spell_description_layout,
    _spell_name_bounds,
    _spell_name_font_size,
    fill_pdf,
    fill_spell_pdf,
)
from utils.utils import get_hero


@pytest.fixture
def output_path():
    path = os.path.join(tempfile.gettempdir(), "test_hero_card.pdf")
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def populated_hero():
    return AncestryHero(
        ancestry_name="Człowiek",
        strength=12,
        dexterity=11,
        intelligence=10,
        will=10,
        perception=10,
        defense=10,
        health=10,
        healing_rate=2,
        size=[1.0],
        speed=10,
        languages=[
            Language(name="Wspólny", can_speak=True, can_write=False),
            Language(name="Elficki", can_speak=True, can_write=True),
        ],
        talents=[Talent(name="Odporność", description="Test talent")],
        professions=["Żołnierz", "Rzemieślnik"],
        backstory={
            "past": "Walczył w wojnie.",
            "personality": "Odważny.",
            "age": "Dorosły.",
            "body": "Silny.",
            "appearance": "Przystojny.",
            "religion": "Wyznawca Nowego Boga.",
        },
        wealth="Klasa średnia",
        oddity="Stary klucz",
        equipment={
            "weapons": [
                {
                    "name": "Miecz",
                    "damage": "1k6+2",
                    "grip": "Jednoręczny",
                    "properties": "",
                },
            ],
            "shields": [],
            "armors": [],
            "backpack": ["plecak", "lina"],
        },
    )


def test_pdf_generation(populated_hero, output_path):
    fill_pdf(populated_hero, output_path)
    assert os.path.exists(output_path)

    with open(output_path, "rb") as f:
        header = f.read(4)
    assert header == b"%PDF"


def test_pdf_fields_populated(populated_hero, output_path):
    fill_pdf(populated_hero, output_path)
    reader = PdfReader(output_path)
    fields = reader.get_form_text_fields() or {}

    assert fields.get("pochodzenie") == "Człowiek"
    assert fields.get("sila") == "12"
    assert fields.get("zrecznosc") == "11"
    assert fields.get("sila_mod") == "2"


def test_pdf_novice_path_is_populated(output_path):
    hero = get_hero("human", is_random=True, level=2, path_name="warrior")

    fill_pdf(hero, output_path)
    fields = PdfReader(output_path).get_form_text_fields() or {}

    assert fields.get("nowicjusz") == "Wojownik"


def test_pdf_weapons_populated(populated_hero, output_path):
    fill_pdf(populated_hero, output_path)
    reader = PdfReader(output_path)
    fields = reader.get_form_text_fields() or {}

    assert fields.get("ekwipunek_1") == "Miecz"
    assert fields.get("obrazenia_1") == "1k6+2"


@pytest.mark.parametrize(
    "ancestry",
    [
        "human",
        "goblin",
        "orc",
        "dwarf",
        "changeling",
        "automaton",
    ],
)
def test_pdf_all_ancestries(ancestry, output_path):
    hero = get_hero(ancestry, is_random=True)
    fill_pdf(hero, output_path)
    assert os.path.exists(output_path)

    with open(output_path, "rb") as f:
        header = f.read(4)
    assert header == b"%PDF"


def test_pdf_talent_placement(output_path):
    hero = AncestryHero(
        ancestry_name="Testowy",
        strength=10,
        dexterity=10,
        intelligence=10,
        will=10,
        perception=10,
        defense=10,
        health=10,
        healing_rate=2,
        size=[1.0],
        speed=10,
        talents=[
            Talent(name="Mały 1", description="S" * 50),
            Talent(name="Kwadrat 1", description="K" * 200),
            Talent(name="Średni 1", description="M" * 300),
            Talent(name="Wielki 1", description="L" * 800),
        ],
    )
    fill_pdf(hero, output_path)
    reader = PdfReader(output_path)
    fields = reader.get_form_text_fields() or {}

    assert fields.get("nazwa_talent_maly_1") == "Mały 1"
    assert fields.get("nazwa_talent_kwadrat_1") == "Kwadrat 1"
    assert fields.get("nazwa_talent_sredni_1") == "Średni 1"
    assert fields.get("nazwa_talent_duzy_1") == "Wielki 1"


def test_pdf_from_full_flow(output_path):
    hero = get_hero("human", is_random=True)

    fill_pdf(hero, output_path)
    assert os.path.exists(output_path)

    reader = PdfReader(output_path)
    fields = reader.get_form_text_fields() or {}
    assert fields.get("pochodzenie") == "Człowiek"
    assert hero.wealth != ""
    assert hero.oddity != ""


def test_generate_filled_spells_pdf_with_nine_names_in_output():
    with open("data_base/spells/air_tradition.json", encoding="utf-8") as file:
        tradition = json.load(file)
    selected_names = [
        "POWIEW", "SZYBOWANIE", "GRZMOT", "DAR LATANIA",
        "PRZYWOŁANIE WICHRU", "ODARCIE ZE SKÓRY", "MARTWE POWIETRZE",
        "GWAŁTOWNY PODMUCH", "PRZEJŚCIE CYKLONU",
    ]
    spell_data = {
        spell["name"]: spell
        for spells_at_level in tradition.values()
        for spell in spells_at_level
    }
    spells = [Spell(**spell_data[name]) for name in selected_names]
    hero = AncestryHero(
        ancestry_name="Człowiek",
        strength=10,
        dexterity=10,
        intelligence=10,
        will=10,
        perception=10,
        defense=10,
        health=10,
        healing_rate=2,
        size=[1.0],
        speed=10,
        spells=spells,
    )
    output_path = os.path.join("output", "filled_spells.pdf")

    fill_spell_pdf(hero, output_path)

    assert os.path.isfile(output_path)


@pytest.mark.parametrize(
    ("name_length", "font_size"),
    [(3, 18), (12, 18), (13, 14), (23, 14), (24, 12), (34, 12)],
)
def test_spell_name_font_size(name_length, font_size):
    assert _spell_name_font_size("A" * name_length) == font_size


@pytest.mark.parametrize(
    ("description_length", "font_size"),
    [(0, 8), (500, 8), (501, 7), (900, 7), (901, 7), (1100, 7), (1101, 7)],
)
def test_spell_description_font_size(description_length, font_size):
    assert _spell_description_font_size("A" * description_length) == font_size


@pytest.mark.parametrize(
    ("description_length", "layout"),
    [
        (0, (8, "empty_spell_cards")),
        (500, (8, "empty_spell_cards")),
        (501, (7, "empty_spell_cards")),
        (900, (7, "empty_spell_cards")),
        (901, (7, "empty_spell_cards")),
        (1100, (7, "empty_spell_cards")),
        (1101, (7, "empty_spell_cards")),
    ],
)
def test_spell_description_layout(description_length, layout):
    assert _spell_description_layout("A" * description_length) == layout


@pytest.mark.parametrize("column", [488, 1239, 1991])
def test_spell_description_bounds_follow_card_edges(column):
    left, width = _spell_description_bounds(column)

    assert left == 100 + (column - 488)
    assert width == 688


def test_spell_name_uses_card_edges_for_wrapping():
    left, width = _spell_name_bounds(488)

    assert left == 170
    assert width == 630
