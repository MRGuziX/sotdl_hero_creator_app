import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.talent import Talent
from utils.pdf_creator import distribute_talents


def test_talent_distribution():

    # 1. Determinacja (Human talent, ~95 chars)
    determinacja = Talent(
        name="Determinacja",
        description="Gdy wyrzucisz 1 na kości ułatwienia, możesz rzucić ponownie i wybrać, którego wyniku użyć",
    )

    # 2. Wspólna odnowa (Cleric talent, ~325 chars)
    wspolna_odnowa = Talent(
        name="Wspólna odnowa",
        description="Możesz użyć akcji, by natychmiast uleczyć tyle obrażeń, ile wynosi twoja Szybkość Zdrowienia. Następnie wybierz jedno stworzenie inne niż ty w bliskim zasięgu. Ono również leczy tyle obrażeń, ile wynosi jego Szybkość Zdrowienia. Po wykorzystaniu tego talentu musisz odbyć pełny odpoczynek, zanim będziesz mógł użyć go ponownie.",
    )

    # 3. A medium talent (~150 chars)
    medium_talent = Talent(name="Medium Talent", description="A" * 150)

    # 4. A huge talent (~700 chars)
    huge_talent = Talent(name="Huge Talent", description="H" * 700)

    # 5. Multiple small talents to fill Small boxes
    small_1 = Talent(name="Small 1", description="S" * 50)
    small_2 = Talent(name="Small 2", description="S" * 50)
    small_3 = Talent(name="Small 3", description="S" * 50)
    small_4 = Talent(name="Small 4", description="S" * 50)  # Should go to Medium

    # 6. A tradition (should be skipped)
    tradition = Talent(
        name="Tradycja: Magia Niebiańska", description="Dostęp do zaklęć"
    )

    talents = [
        determinacja,
        wspolna_odnowa,
        medium_talent,
        huge_talent,
        small_1,
        small_2,
        small_3,
        small_4,
        tradition,
    ]

    assigned, overflow = distribute_talents(talents)


    # Assertions
    assert "kwadrat_2" in assigned  # determinacja (95 chars)
    assert "sredni_1" in assigned  # wspolna_odnowa (327 chars)
    assert "kwadrat_1" in assigned  # medium_talent (150 chars)
    assert "duzy_1" in assigned  # huge_talent (700 chars)
    assert "maly_1" in assigned  # small_1 (50 chars)
    assert "maly_2" in assigned  # small_2 (50 chars)
    assert "maly_3" in assigned  # small_3 (50 chars)
    assert "sredni_2" in assigned  # small_4 (50 chars)
    assert len(overflow) == 0

    # Check that tradition was NOT assigned and NOT in overflow
    assigned_names = [d["name"] for d in assigned.values()]
    assert "Tradycja: Magia Niebiańska" not in assigned_names
    assert len(assigned) == 8  # 9 total - 1 tradition = 8 assigned

    # Add 10 more huge talents to force overflow
    extra_talents = [
        Talent(name=f"Overflow {i}", description="O" * 1500) for i in range(5)
    ]
    assigned_2, overflow_2 = distribute_talents(extra_talents)
    assert len(overflow_2) == 4

