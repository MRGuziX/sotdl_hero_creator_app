import json
import os
import tempfile
from io import BytesIO

import pytest
from pypdf import PdfReader

from models.base_hero import AncestryHero
from models.language import Language
from models.spell import Spell
from models.talent import Talent
from utils.pdf_creator import (
    _format_spell_description,
    _spell_card_fields,
    _spell_critical_success_y,
    _spell_description_bounds,
    _spell_description_font_size,
    _spell_description_layout,
    _spell_description_top,
    _spell_effect_value,
    _spell_name_bounds,
    _spell_name_font_size,
    _spell_origin_text,
    _spell_origin_offset_y,
    _spell_origin_x,
    _spell_table_top,
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


def test_spell_card_renders_all_fields_together():
    spell = Spell(
        name="OSOBLIWOŚĆ",
        card_description="W punkcie początkowym pojawia się wirująca plama. Gdy rzucasz osobliwość, niezabezpieczone obiekty wewnątrz jej obszaru przemieszczają się o 2k6 metrów w kierunku punktu początkowego. Każde stworzenie znajdujące się wewnątrz obszaru w momencie jego rzucenia lub na niego wchodzące musi wykonać test Siły z 1 utrudnieniem. Porażka oznacza, że przemieszcza się o 2k6 metrów w kierunku punktu początkowego i dopóki czar trwa , nie może się od niego oddalić. Stworzenie lub obiekt, które dotrze do punktu początkowego osobliwości, otrzymuje 10k6 obrażeń. Jeśli wskutek tych obrażeń zostanie obezwładnione, dojdzie także do całkowitego wymazania go z rzeczywistości. Gdy efekt czaru dobiegnie końca, plama wybucha, zadając 4k6 obrażeń wszystkiemu wewnątrz obszaru działania zaklęcia. Każde znajdujące się tam stworzenie musi wykonać test Siły. Porażka oznacza, że zostaje powalone, a sukces, że otrzymuje tylko połowę obrażeń.",
        target=(
            "Cel: Jeden obiekt o Rozmiarze 1 lub mniejszym w średnim zasięgu, "
            "który widzisz. Celem nie może być obiekt, który kiedykolwiek był "
            "stworzeniem."
        ),
        # area=(
        #     "Obszar: Linia łamana o długości 10 metrów, wysokości 5 metrów i "
        #     "szerokości 2 metrów, o punkcie początkowym w dalekim zasięgu i "
        #     "dowolnym kierunku, pod warunkiem że co najmniej dwa krańcowe "
        #     "segmenty opierają się o twarde podłoże."
        # ),
        duration="Czas działania: Dopóki nie odbędziesz pełnego odpoczynku; patrz niżej.",
        critical_success="Rzut na atak 20+: Cel otrzymuje dodatkowe 1k6 obrażeń.",
        requirements="Musisz znajdować się na wolnym powietrzu.",
        sacrifice="Możesz poświęcić użycie tego zaklęcia.",
        tags=["Magia Testowa", "Atak"],
        level=2,
    )
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
        spells=[spell],
    )
    output_path = os.path.join("output", "filled_spells.pdf")

    fill_spell_pdf(hero, output_path)


def test_real_storm_and_conjuration_spells_render_from_full_json():
    lightning_data = {
        "name": "PRZYWOŁANIE PIORUNA",
        "tags": ["Magia Burzy", "Atak"],
        "level": 2,
        "requirements": "Wymagania: Musisz znajdować się na wolnym powietrzu.",
        "target": "Cel: Punkt na podłożu w dalekim zasięgu.",
        "sacrifice": (
            "Poświęcenie: Możesz poświęcić użycie tego zaklęcia, "
            "by rzucić czar rozwidlony piorun."
        ),
        "book_description": (
            "W cel uderza z nieba piorun, zadając 3k6 + 5 obrażeń "
            "wszystkiemu w promieniu 3 metrów od niego. Każde stworzenie, "
            "które otrzyma w ten sposób obrażenia, musi wykonać test Siły. "
            "Porażka oznacza, że staje się ogłuszone na 1 godzinę, a sukces, "
            "że otrzymuje tylko połowę obrażeń."
        ),
        "card_description": (
            "W cel uderza piorun, zadając\n3k6 + 5 obrażeń wszystkiemu\n"
            "w promieniu 3m. Każde stworzenie,\nktóre otrzyma w ten sposób\n"
            "obrażenia, wykonuje test Siły.\nPorażka oznacza, że staje się\n"
            "ogłuszone na 1 godzinę, a sukces,\nże otrzymuje tylko połowę obrażeń."
        ),
        "origin": {"source": "PG", "number": 127},
    }
    item_data = {
        "name": "PRZYWOŁANIE UŻYTECZNEGO PRZEDMIOTU",
        "tags": ["Przywołania", "Użytkowe"],
        "level": 0,
        "area": "Obszar: Sześcian o krawędzi 1 metra i punkcie początkowym w zasięgu ręki.",
        "duration": "Czas działania: 1 minuta.",
        "book_description": (
            "Wewnątrz obszaru działania zaklęcia pojawia się przedmiot "
            "o Rozmiarze 1 lub mniejszym, który nie jest magiczny ani wart "
            "więcej niż 1 srebrnik."
        ),
        "card_description": "",
        "origin": {"source": "PG", "number": 140},
    }
    wall_data = {
        "name": "ŚCIANA MIECZY",
        "tags": ["Magia Bitewna", "Atak"],
        "level": 4,
        "area": (
            "Obszar: Linia o długości 20 metrów, wysokości 5 metrów "
            "i szerokości 2 metrów o punkcie początkowym w dalekim zasięgu."
        ),
        "duration": "Czas działania: 1 godzina.",
        "book_description": (
            "W obszarze działania zaklęcia na czas jego trwania powstaje "
            "ściana tnących ostrzy. Zapewnia ona całkowitą osłonę wszystkiemu, "
            "co znajduje się za nią. Gdy ostrza się pojawiają, wszystko "
            "wewnątrz tego obszaru otrzymuje 5k6 obrażeń. Każde stworzenie, "
            "które wykona udany test Zręczności, otrzymuje tylko połowę tych "
            "obrażeń. Stworzenia mogą przemieszczać się przez obszar działania "
            "zaklęcia jak po trudnym terenie. Gdy istota wkroczy na niego z "
            "zewnątrz lub jeśli znajduje się w nim na koniec rundy, musi wykonać "
            "udany test Zręczności, w przeciwnym wypadku otrzymuje 3k6 obrażeń."
        ),
        "card_description": (
            "W obszarze działania zaklęcia na czas\njego trwania powstaje ściana "
            "tnących ostrzy. Zapewnia ona całkowitą osłonę\nwszystkiemu, co "
            "znajduje się za nią. Gdy\nostrza się pojawiają, wszystko wewnątrz\n"
            "tego obszaru otrzymuje 5k6 obrażeń.\nKażde stworzenie, które wykona "
            "udany test\nZręczności, otrzymuje tylko połowę tych\nobrażeń. "
            "Stworzenia mogą przemieszczać\nsię przez obszar działania zaklęcia "
            "jak\npo trudnym terenie. Gdy istota wkroczy\nna niego z zewnątrz "
            "lub jeśli znajduje się\nw nim na koniec rundy, musi wykonać\n"
            "udany test Zręczności, w przeciwnym\nwypadku otrzymuje 3k6 obrażeń."
        ),
        "origin": {"source": "PG", "number": 127},
    }
    toad_data = {
        "name": "ROPUCHA",
        "tags": ["Klątwy", "Atak"],
        "level": 4,
        "target": "Cel: Jedno żywe stworzenie w średnim zasięgu, które widzisz.",
        "duration": "Czas działania: Koncentracja do 1 minuty; patrz niżej.",
        "critical_success": (
            "Rzut na atak to 20+: Nie trzeba spełnić żadnych warunków, aby klątwa "
            "trwała, dopóki żyjesz lub dopóki sam nie poświęcisz akcji na jej "
            "zdjęcie, mając cel w średnim zasięgu."
        ),
        "book_description": (
            "Wykonaj oparty na Intelekcie rzut na atak przeciwko Sile celu – z 3 "
            "ułatwieniami, jeśli jego Zdrowie wynosi 40 lub mniej. Sukces oznacza, "
            "że ofiara zamienia się w nieszkodliwą ropuchę (drobne zwierzę) i "
            "pozostaje w tej postaci, dopóki utrzymujesz koncentrację (maksymalnie "
            "na 1 minutę). Jeśli przez czas działania zaklęcia nic nie przerwie "
            "twojej koncentracji, klątwa ta trwa, dopóki żyjesz lub dopóki nie "
            "poświęcisz akcji, aby ją zdjąć. Zostaje jednak przełamana, gdy ropuchę "
            "z własnej woli pocałuje dziewica."
        ),
        "card_description": (
            "Wykonaj oparty na Intelekcie rzut na\n"
            "atak przeciwko Sile celu – z 3 ułatwieniami,\n"
            "jeśli jego Zdrowie wynosi 40 lub mniej.\n"
            "Sukces oznacza, że ofiara zamienia się\n"
            "w ropuchę (drobne zwierzę) i pozostaje w tej\n"
            "postaci, dopóki utrzymujesz koncentrację\n"
            "(maksymalnie na 1 minutę). Jeśli przez czas\n"
            "działania zaklęcia nic nie przerwie twojej\n"
            "koncentracji, klątwa ta trwa, dopóki żyjesz\n"
            "lub dopóki nie poświęcisz akcji, aby ją zdjąć"
        ),
        "origin": {"source": "PG", "number": 125},
    }
    def load_spell(file_name, level, spell_name):
        with open(f"data_base/spells/{file_name}.json", encoding="utf-8") as file:
            data = json.load(file)
        return next(spell for spell in data[f"level_{level}"] if spell["name"] == spell_name)

    lightning_data = load_spell("storm_tradition", 2, "PRZYWOŁANIE PIORUNA")
    item_data = load_spell(
        "conjuration_tradition", 0, "PRZYWOŁANIE UŻYTECZNEGO PRZEDMIOTU"
    )
    wall_data = load_spell("chaos_tradition", 1, "ZAKRZYWIENIE PRZESTRZENI")
    toad_data = load_spell("curse_tradition", 4, "ROPUCHA")
    vision_data = load_spell("divination_tradition", 4, "WIZJA")
    illusion_data = load_spell("illusion_tradition", 2, "UROJENIA")
    duplicates_data = load_spell("illusion_tradition", 1, "DUPLIKATY")
    mirage_data = load_spell("illusion_tradition", 4, "MIRAŻ")
    wild_magic_data = load_spell("chaos_tradition", 3, "DZIKA MAGIA")
    healing_data = load_spell("life_tradition", 1, "UZDROWIENIE")
    hateful_defecation_data = load_spell(
        "forbidden_tradition", 1, "NIENAWISTNA DEFEKACJA"
    )
    soul_swap_data = load_spell("forbidden_tradition", 4, "ZAMIANA DUSZ")
    vile_fusion_data = load_spell("forbidden_tradition", 5, "NIKCZEMNE ZESPOLENIE")
    magical_item_data = load_spell("technomancy_tradition", 5, "MAGICZNY PRZEDMIOT")
    spells = [
        Spell(**data)
        for data in (
            lightning_data,
            item_data,
            wall_data,
            toad_data,
            vision_data,
            illusion_data,
            duplicates_data,
            mirage_data,
            wild_magic_data,
            healing_data,
            hateful_defecation_data,
            soul_swap_data,
            vile_fusion_data,
            magical_item_data,
        )
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




def test_spell_card_fields_include_requirements_and_sacrifice():
    spell = Spell(
        name="TEST",
        description="Opis",
        requirements="Musisz znajdować się na wolnym powietrzu.",
        sacrifice="Możesz poświęcić użycie tego zaklęcia.",
    )

    fields = _spell_card_fields(spell, 1)

    assert fields["spell_requirements_card_1"] == spell.requirements
    assert fields["spell_sacrifice_card_1"] == spell.sacrifice


def test_spell_card_fields_include_permanent_effect():
    spell = Spell(
        name="TEST",
        description="Opis",
        permanent="Jeśli zaklęcie trwa wystarczająco długo, efekt staje się permanentny.",
    )

    fields = _spell_card_fields(spell, 1)

    assert fields["spell_permanent_card_1"] == spell.permanent


def test_spell_card_fields_include_table():
    table = {
        "headers": ["Liczba duplikatów", "W duplikat trafia wynik"],
        "rows": [[4, "16 lub mniej"], [3, "15 lub mniej"], [2, "14 lub mniej"], [1, "10 lub mniej"]],
    }
    spell = Spell(name="DUPLIKATY", table=table)

    fields = _spell_card_fields(spell, 1)

    assert fields["spell_table_card_1"] == table


def test_spell_table_gives_effect_column_more_space_and_wraps_text():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfgen.canvas import Canvas

    from utils.pdf_creator import SPELL_FONT_BOLD, _draw_spell_table, _spell_table_column_widths

    table = {
        "headers": ["K20", "Efekt"],
        "rows": [["4-5", "Stworzenia wykonują bardzo długi efekt, który powinien zawinąć się w komórce tabeli."]],
    }
    canvas = Canvas(BytesIO())

    height = _draw_spell_table(canvas, table, 100, 500, 688, 1, 1)

    assert height > 11
    widths = _spell_table_column_widths(table["headers"], 688)
    assert widths[0] >= pdfmetrics.stringWidth("K20", SPELL_FONT_BOLD, 6) + 8
    assert widths[1] >= pdfmetrics.stringWidth("Efekt", SPELL_FONT_BOLD, 6) + 8
    canvas.save()


def test_wild_magic_contains_k20_effect_table():
    with open("data_base/spells/chaos_tradition.json", encoding="utf-8") as file:
        data = json.load(file)

    spell = next(spell for spell in data["level_3"] if spell["name"] == "DZIKA MAGIA")
    table = spell["table"]

    assert table["headers"] == ["K20", "Efekt"]
    assert [row[0] for row in table["rows"]] == [
        "1",
        "2-3",
        "4-5",
        "6-8",
        "9-13",
        "14-15",
        "16-17",
        "18-19",
        "20",
    ]
    assert table["rows"][0][1] == "Pojawia się 1k6 małych, wrogich demonów."
    assert table["rows"][-1][1] == "Odzyskujesz jedno użycie zaklęcia 3 lub niższego kręgu."


@pytest.mark.parametrize(
    "value",
    [
        "Rzut na atak 20+: Nie trzeba spełnić warunków.",
        "Rzut na atak to 20+: Nie trzeba spełnić warunków.",
    ],
)
def test_spell_effect_prefix_is_not_duplicated(value):
    assert _spell_effect_value(value, "Rzut na atak 20+:") == "Nie trzeba spełnić warunków."


def test_spell_description_starts_each_bullet_on_new_line():
    formatted = _format_spell_description("Opis. • Pierwszy punkt.\n• Drugi punkt.")

    assert formatted == "Opis.<br/>• Pierwszy punkt.<br/>• Drugi punkt."


def test_spell_description_formats_reaction_as_bold_new_section():
    formatted = _format_spell_description(
        "Opis zaklęcia. Reakcja: Możesz rzucić zaklęcie jako reakcję."
    )

    assert formatted == (
        'Opis zaklęcia.<br/><font name="Athelas-Bold">Reakcja:</font> '
        "Możesz rzucić zaklęcie jako reakcję."
    )


def test_spell_description_formats_reaction_at_start_without_extra_break():
    formatted = _format_spell_description("Reakcja: Natychmiastowy efekt.")

    assert formatted == '<font name="Athelas-Bold">Reakcja:</font> Natychmiastowy efekt.'


def test_spell_tags_include_level():
    spell = Spell(
        name="POWIEW",
        description="Opis",
        tags=["Powietrze", "Atak"],
        level=1,
    )

    fields = _spell_card_fields(spell, 1)

    assert fields["spell_tags_card_1"] == "Powietrze, Atak 1"


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


def test_spell_critical_success_moves_below_wrapped_description():
    base_y = 135
    px_to_y = 0.2

    short_description_y = _spell_critical_success_y(base_y, 20, px_to_y)
    long_description_y = _spell_critical_success_y(base_y, 100, px_to_y)

    assert short_description_y == 620
    assert long_description_y == 1020
    assert long_description_y > short_description_y


def test_spell_description_starts_50_pixels_below_last_technical_field():
    assert _spell_description_top(135, 300) == 350
    assert _spell_description_top(135, None) == 470


def test_spell_table_starts_25_pixels_below_description():
    assert _spell_table_top(350, 100, 0.2) == 875


def test_spell_origin_is_formatted_for_card_footer():
    assert _spell_origin_text({"source": "PG", "number": 153}) == "PG 153"
    assert _spell_origin_text({}) == ""


def test_spell_origin_uses_the_same_left_offset_for_each_column():
    assert _spell_origin_x(488) == 168
    assert _spell_origin_x(1249) == 929
    assert _spell_origin_x(1991) == 1671


def test_spell_origin_has_an_offset_for_each_row():
    assert _spell_origin_offset_y(0) == 980
    assert _spell_origin_offset_y(1) == 980
    assert _spell_origin_offset_y(2) == 900
