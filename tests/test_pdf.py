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
    spells = [
        Spell(
            name="POWIEW",
            description="W obszarze działania zaklęcia wywołujesz niewielki powiew, który przemieszcza się wraz z tobą. Rozprasza on zapachy i zwiewa kurz, rozrzuca lekkie przedmioty, takie jak kartki, gasi świece, a większe płomienie pod jego wpływem tańczą i migoczą. Stworzenia wewnątrz obszaru działania zaklęcia, które atakują cię bronią dystansową lub miotaną, wykonują rzuty na atak z 1 utrudnieniem.",
        ),
        Spell(
            name="SZYBOWANIE",
            description="Reakcja: Możesz rzucić to zaklęcie jako reakcję, gdy widzisz spadający cel. Przez czas trwania zaklęcia nie otrzyma on obrażeń od upadku. Jeśli w momencie zakończenia efektu czaru istota nadal będzie spadać, wartość obrażeń od upadku należy liczyć od miejsca, w którym się znajdowała, gdy zaklęcie przestało działać.",
        ),
        Spell(
            name="PRZYWOŁANIE UŻYTECZNEGO PRZEDMIOTU",
            description="Ze środka obszaru działania zaklęcia rozchodzi się ogłuszający hałas, zadając 1k6 + 1 obrażeń wszystkiemu wewnątrz. Każde znajdujące się tam stworzenie musi wykonać test Siły; sukces oznacza, że otrzymuje tylko połowę obrażeń. Porażka oznacza, że zostaje ono także ogłuszone na 1 minutę.",
        ),
        Spell(
            name="DAR LATANIA",
            description="Dotknij celu. Na czas trwania zaklęcia może on latać ze swoją zwykłą Prędkością.",
        ),
        Spell(
            name="PRZYWOŁANIE WICHRU",
            description="Zawodzący wiatr rozprasza opary, mgłę, dym i gazy w obszarze działania zaklęcia. Nieosłonięte płomienie zostają zgaszone, a lekkie przedmioty zdmuchnięte ku najbliższej granicy obszaru. Każda istota w obszarze działania zaklęcia musi wykonać udany test Siły, w przeciwnym wypadku zostaje odepchnięta od punktu początkowego na 1k6 metrów. Stworzenia latające wykonują ten test z 1 utrudnieniem.",
        ),
        Spell(
            name="ODARCIE ZE SKÓRY",
            description="Uderzasz w cel porwanym przez wiatr ostrym piaskiem. Wykonaj oparty na Woli rzut na atak przeciwko Sile celu. Sukces oznacza, że otrzymuje on 2k6 + 3 obrażeń. Żywe stworzenie, które zostanie obezwładnione wskutek tego ataku, natychmiast umiera; pozostają po nim jedynie odarte z ciała kości.",
        ),
        Spell(
            name="MARTWE POWIETRZE",
            description="Przez czas trwania zaklęcia żaden dźwięk ani nie wydobywa się z objętego działaniem obszaru, ani nie dociera do jego wnętrza. Znajdujące się wewnątrz stworzenia są ogłuszone i niewrażliwe na wszelkie ataki dźwiękiem, takie jak zaklęcie grzmot.",
        ),
        Spell(
            name="GWAŁTOWNY PODMUCH",
            description="Z punktu początkowego dobywa się potężne uderzenie wiatru. Każde stworzenie wewnątrz obszaru działania zaklęcia musi wykonać test Siły; te o Rozmiarze 1 lub mniejszym wykonują go z 1 utrudnieniem. Porażka oznacza, że istota zostaje powalona i odepchnięta od punktu początkowego na 5k6 metrów.",
        ),
        Spell(
            name="PRZEJŚCIE CYKLONU",
            description="Potężna trąba powietrzna pojawia się na jednym końcu obszaru działania zaklęcia i przemieszcza się ku drugiemu, zadając 3k6 obrażeń wszystkim stworzeniom i obiektom, przez których przestrzeń przejdzie. Każde stworzenie, które otrzyma w ten sposób obrażenia, musi wykonać test Siły. Porażka oznacza, że zostaje odepchnięte o 1k6 metrów, a następnie powalone.",
        ),
        # target="...", duration="...", area="...", tags=[...], critical_success="...",
    ]
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
