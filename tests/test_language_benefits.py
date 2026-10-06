import pytest

from models.action import AddLanguage, GrantLiteracy, UpdateLanguage
from models.language import Language
from utils.utils import add_language, apply_action, expand_any_to_choices


@pytest.mark.parametrize("random_mode", [False, True])
def test_new_literate_language_is_added(hero, random_mode):
    add_language("Elficki", hero, can_write=True, is_random=random_mode)
    assert [
        (language.name, language.can_speak, language.can_write) for language in hero.languages
    ] == [("Elficki", True, True)]


@pytest.mark.parametrize("action", [GrantLiteracy(target="any"), UpdateLanguage(name="known")])
def test_literacy_placeholder_becomes_a_real_choice(hero, action):
    hero.languages = [Language(name="Wspólny", can_speak=True, can_write=False)]
    remaining, groups = expand_any_to_choices(hero, [action], [])
    assert not remaining
    assert len(groups) == 1
    assert groups[0]
    apply_action(groups[0][0], hero)
    assert hero.languages[0].can_write


def test_repeated_language_learning_does_not_duplicate_or_remove_literacy(hero):
    apply_action(AddLanguage(name="Elficki", can_write=True), hero)
    apply_action(AddLanguage(name="Elficki", can_write=False), hero)
    assert len(hero.languages) == 1
    assert hero.languages[0].can_write
