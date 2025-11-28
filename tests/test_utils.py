from utils.utils import (
    add_profession,
    add_language,
    add_wealth,
    add_oddity,
    add_money,
    add_armor,
    add_weapon,
    add_shield,
)

character_data = {
    "actions": [
        {
            "add_attribute": {
                "any": 1
            }
        },
        {
            "add_attribute": {
                "profession": "naukowa"
            }
        }
    ],
    "backstory": {
        "age": "Dorosły w średnim wieku, 36–55 lat.",
        "appearance": "Posiadasz kilka cech fizycznych, które dodają ci atrakcyjności.",
        "body": "Jesteś średniego wzrostu i wagi.",
        "character": "Ponad wszystkim innym stawiasz dobro swoje i swoich bliskich.",
        "past": "Zakochałeś się; związek ten nadal trwa lub zakończył się dobrze.",
        "religion": "Jesteś wyznawcą Nowego Boga."
    },
    "choices": [
        {
            "language": {
                "known": False,
                "name": "any"
            },
            "profession": "any"
        }
    ],
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
    "professions": [
    ],
    "spells": [
    ],
    "wealth": "",
    "money": [
        {
            "name": "okrawki",
            "amount": 0
        },
        {
            "name": "miedziaki",
            "amount": 0
        },
        {
            "name": "srebrniki",
            "amount": 0
        },
        {
            "name": "złote korony",
            "amount": 0
        }
    ], "oddity": "",
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
            'backpack': []
        }
    ],
    "talents": [
        {
            "description": "",
            "level": 0,
            "name": ""
        },
        {
            "description": "",
            "name": ""
        }
    ]
}


def test_profession_method():
    add_profession(
        profession_type="any",
        character_data=character_data,
        is_random=True
    )


def test_add_language():
    add_language(
        language_type="custom",
        known=False,
        character_data=character_data,
    )


def test_wealth():
    add_wealth(character_data)


def test_oddity():
    add_oddity(character_data)


def test_add_money():
    add_money(
        amount=10,
        money_type="miedziaki",
        character_data=character_data
    )
    print("x")


def test_add_armors():
    add_armor(
        item_name="Miękka skórznia",
        character_data=character_data
    )


def test_add_weapon():
    add_weapon(
        item_name="Oszczep",
        character_data=character_data
    )


def test_add_shields():
    add_shield(
        item_name="Duża tarcza",
        character_data=character_data
    )
