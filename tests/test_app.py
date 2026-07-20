import os

import pytest

from main import app, OUTPUT_PATH
from models.action import AddSpell, AddTradition
from models.action import AddTalent
from models.base_hero import AncestryHero
from models.spell import Spell
from models.talent import Talent
from utils.utils import _expand_dynamic_choice_group
from utils.utils import apply_action


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_index_route(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"cwd_logo.png" in response.data


def test_roll_ancestry_route(client):
    ancestries = ["human", "automaton", "goblin", "dwarf", "orc", "changeling"]
    for ancestry in ancestries:
        response = client.get(f'/roll/{ancestry}')
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/pdf'


def test_roll_invalid_ancestry(client):
    response = client.get('/roll/elf')
    assert response.status_code == 400
    assert b"Invalid ancestry" in response.data


def test_roll_random_route(client):
    response = client.get('/roll_random', follow_redirects=True)
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/pdf'


def test_static_logo(client):
    response = client.get('/static/cwd_logo.png')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'image/png'


def test_download_current_route(client):
    client.get('/roll/human')

    response = client.get('/download_current')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/pdf'


def test_download_no_hero(client):
    backup_path = OUTPUT_PATH + ".bak"
    exists = os.path.exists(OUTPUT_PATH)
    if exists:
        os.rename(OUTPUT_PATH, backup_path)

    try:
        response = client.get('/download_current')
        assert response.status_code == 404
        assert b"No hero generated yet" in response.data
    finally:
        if exists:
            if os.path.exists(OUTPUT_PATH):
                os.remove(OUTPUT_PATH)
            os.rename(backup_path, OUTPUT_PATH)


def test_roll_manual_returns_choices(client):
    response = client.get('/roll/human?is_random=0')
    assert response.status_code == 200
    data = response.get_json()
    if data and data.get("status") == "need_choices":
        assert "hero_data" in data
        assert "choices" in data


def test_confirm_choices(client):
    response = client.get('/roll/human?is_random=0')
    data = response.get_json()

    if data and data.get("status") == "need_choices":
        hero_data = data["hero_data"]
        choices = data["choices"]
        selected = [group[0] for group in choices]

        response = client.post('/confirm_choices', json={
            "hero_data": hero_data,
            "selected_choices": selected,
        })
        assert response.status_code == 200
        result = response.get_json()
        assert result["status"] in {"need_choices", "success"}
        if result["status"] == "need_choices":
            assert result["choices"]
            assert result["choice_cursor"] == 1


def test_confirm_choices_advances_repeated_attribute_groups(client):
    response = client.get('/roll/human?is_random=0')
    data = response.get_json()
    assert data["status"] == "need_choices"

    first = client.post('/confirm_choices', json={
        "hero_data": data["hero_data"],
        "selected_choices": [data["choices"][0][0]],
    }).get_json()
    assert first["status"] == "need_choices"
    assert first["choice_cursor"] == 1

    second = client.post('/confirm_choices', json={
        "hero_data": first["hero_data"],
        "selected_choices": [first["choices"][0][0]],
        "choice_cursor": first["choice_cursor"],
    }).get_json()
    assert second["status"] in {"need_choices", "success"}
    if second["status"] == "need_choices":
        assert second["choice_cursor"] == 2


def test_index_lists_all_novice_paths(client):
    response = client.get('/')
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    for path_id in ("cleric", "mage", "rouge", "warrior"):
        assert f"selectPath('{path_id}'" in page


def test_new_novice_paths_can_start_manual_creation(client):
    for path_id in ("mage", "rouge", "warrior"):
        response = client.get(f'/roll/human?is_random=0&level=2&path={path_id}')
        assert response.status_code == 200
        assert response.get_json()["status"] == "need_choices"


def test_new_tradition_choice_excludes_known_traditions(monkeypatch):
    monkeypatch.setattr(
        "utils.utils._load_json",
        lambda path: {"Stara Wiara": ["życie", "ogień", "woda"]},
    )
    hero = AncestryHero(
        ancestry_name="Człowiek",
        ancestry_id="human",
        religion="Stara Wiara",
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
    hero.talents.append(Talent(name="Tradycja: życie", description=""))

    choices = _expand_dynamic_choice_group(
        hero,
        [AddTradition(name="religious_tradition")],
    )

    assert [choice.name for choice in choices] == ["ogień", "woda"]


def test_known_tradition_spell_choice_filters_known_spells_and_power(monkeypatch):
    monkeypatch.setattr(
        "utils.utils._load_json",
        lambda path: {
            "level_0": [{"name": "leczenie"}, {"name": "odnowa"}],
            "level_1": [{"name": "zaklęcie poziomu 1"}],
            "level_2": [{"name": "zaklęcie poziomu 2"}],
        },
    )
    hero = AncestryHero(
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
        power=2,
    )
    hero.talents.append(Talent(name="Tradycja: Życie", description=""))
    hero.spells.append(Spell(name="leczenie", description="", level=0))

    choices = _expand_dynamic_choice_group(
        hero,
        [AddSpell(name="known_tradition")],
    )

    assert [choice.name for choice in choices] == [
        "odnowa", "zaklęcie poziomu 1", "zaklęcie poziomu 2"
    ]


def test_repeated_talent_upgrades_existing_talent():
    hero = AncestryHero(
        ancestry_name="Człowiek", ancestry_id="human", strength=10, dexterity=10,
        intelligence=10, will=10, perception=10, defense=10, health=10,
        healing_rate=1, size=[1.0, 1.0], speed=10,
    )
    first = AddTalent(name="Cios w plecy", description="1k6 obrażeń")
    second = AddTalent(
        name="Cios w plecy", description="1k6 obrażeń",
        upgrade="2k6 obrażeń",
    )

    apply_action(first, hero)
    apply_action(second, hero)

    assert len(hero.talents) == 1
    assert hero.talents[0].name == "Cios w plecy (poz. 2)"
    assert hero.talents[0].description == "2k6 obrażeń"


def test_repeated_backstab_uses_full_upgraded_description():
    hero = AncestryHero(
        ancestry_name="Człowiek", ancestry_id="human", strength=10, dexterity=10,
        intelligence=10, will=10, perception=10, defense=10, health=10,
        healing_rate=1, size=[1.0, 1.0], speed=10,
    )
    description = (
        "Raz na rundę, gdy atakujesz bronią prostą lub szybką i wykonujesz "
        "rzut na atak z co najmniej 1 ułatwieniem, atak ten zadaje dodatkowe "
        "1k6 obrażeń."
    )
    apply_action(AddTalent(name="Cios w plecy", description=description), hero)
    apply_action(
        AddTalent(
            name="Cios w plecy",
            description=description,
            upgrade="Jeśli wybierzesz ten talent ponownie, dodatkowe obrażenia zwiększają się do 2k6.",
        ),
        hero,
    )

    assert hero.talents[0].description == description.replace("1k6", "2k6")


def test_rouge_repeatable_talent_contains_upgrade_metadata():
    hero, choices = __import__("utils.utils", fromlist=["get_hero"]).get_hero(
        "human", is_random=False, level=8, path_name="rouge"
    )
    backstab_options = [
        option for group in choices for option in group
        if isinstance(option, AddTalent) and option.name == "Cios w plecy"
    ]

    assert backstab_options
    assert all(option.upgrade and "2k6" in option.upgrade for option in backstab_options)


def test_rouge_talent_selection_is_one_group_of_five_options():
    _, choices = __import__("utils.utils", fromlist=["get_hero"]).get_hero(
        "human", is_random=False, level=8, path_name="rouge"
    )

    rogue_talent_groups = [
        group for group in choices
        if {option.name for option in group if isinstance(option, AddTalent)}
        == {"Cios w plecy", "Pogróżki", "Magia", "Wolta", "Zwód"}
    ]

    assert len(rogue_talent_groups) == 2
    assert all(len(group) == 5 for group in rogue_talent_groups)


def test_level_eight_wolta_uses_upgrade_description_when_selected_again():
    hero, choices = __import__("utils.utils", fromlist=["get_hero"]).get_hero(
        "human", is_random=False, level=8, path_name="rouge"
    )
    wolta = next(
        option for group in choices for option in group
        if isinstance(option, AddTalent) and option.name == "Wolta"
    )

    apply_action(wolta, hero)
    apply_action(wolta, hero)

    upgraded = next(talent for talent in hero.talents if talent.name.startswith("Wolta"))
    assert upgraded.name == "Wolta (poz. 2)"
    assert upgraded.description == wolta.upgrade


@pytest.mark.parametrize(
    ("name", "description", "upgrade"),
    [
        (
            "Cios w plecy",
            "Atak zadaje dodatkowe 1k6 obrażeń.",
            "Jeśli wybierzesz ten talent ponownie, dodatkowe obrażenia zwiększają się do 2k6.",
        ),
        (
            "Pogróżki",
            "Przeciwnik zostaje przestraszony.",
            "Jeśli wybierzesz ten talent ponownie, twoje ataki bronią zadają przestraszonym w ten sposób celom dodatkowe 1k6 obrażeń.",
        ),
        (
            "Magia",
            "Poznajesz jedną tradycję magiczną.",
            "Jeśli wybierzesz ten talent ponownie, zwiększasz swoją Moc o 1 i poznajesz jedną tradycję lub uczysz się jednego zaklęcia.",
        ),
        (
            "Wolta",
            "Możesz poruszyć się o połowę swojej Prędkości.",
            "Jeśli wybierzesz ten talent ponownie, możesz poruszyć się o całą wartość swojej Prędkości.",
        ),
        (
            "Zwód",
            "Przeciwnik zostaje zauroczony.",
            "Jeśli wybierzesz ten talent ponownie, zyskujesz 1 ułatwienie do związanego z nim rzutu i możesz zwodzić stworzenia, które cię nie rozumieją.",
        ),
    ],
)
def test_every_rouge_talent_uses_its_upgrade_description(name, description, upgrade):
    hero = AncestryHero(
        ancestry_name="Człowiek", ancestry_id="human", strength=10, dexterity=10,
        intelligence=10, will=10, perception=10, defense=10, health=10,
        healing_rate=1, size=[1.0, 1.0], speed=10,
    )

    apply_action(AddTalent(name=name, description=description), hero)
    apply_action(AddTalent(name=name, description=description, upgrade=upgrade), hero)

    assert len(hero.talents) == 1
    expected = description.replace("1k6", "2k6") if name == "Cios w plecy" else upgrade
    assert hero.talents[0].description == expected
