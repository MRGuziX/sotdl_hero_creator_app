from utils.utils import add_profession, add_language

character_data = {'actions': [{'add_attribute': {'any': 1}}, {'add_attribute': {'profession': 'any'}}],
                  'backstory': {'age': 'Dorosły w średnim wieku, 36–55 lat.',
                                'appearance': 'Posiadasz kilka cech fizycznych, które dodają ci atrakcyjności.',
                                'body': 'Jesteś średniego wzrostu i wagi.',
                                'character': 'Ponad wszystkim innym stawiasz dobro swoje i swoich bliskich.',
                                'past': 'Zakochałeś się; związek ten nadal trwa lub zakończył się dobrze.',
                                'religion': 'Jesteś wyznawcą Nowego Boga.'},
                  'choices': [{'language': {'known': False, 'name': 'any'}, 'profession': 'any'}],
                  'general': {'ancestry_name': 'Człowiek', 'corruption': 0, 'damage': 0, 'defense': 10, 'dexterity': 11,
                              'healing_rate': 2, 'health': 10, 'insanity': 0, 'intelligence': 10,
                              'language': [{'known': False, 'name': 'Wspólny'}, {'known': True, 'name': 'Elficki'}], 'perception': 10, 'power': 0,
                              'size': [1.0, 0.5], 'speed': 10, 'strength': 10, 'will': 10},
                  'professions': [{'description': '', 'name': ''}], 'spells': [],
                  'talents': [{'description': '', 'level': 0, 'name': ''}, {'description': '', 'name': ''}]}


def test_profession_method():
    add_profession(
        profession_type="naukowa",
        character_data=character_data
    )

def test_add_language():
    add_language(
        language_type="any",
        known=True,
        character_data=character_data,
        is_random=True
    )
