import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.talent import Talent
from utils.pdf_creator import distribute_talents


def test_talent_distribution():
    small_talent = Talent(name="Small", description="S" * 100)
    medium_talent = Talent(name="Medium", description="M" * 300)
    big_talent = Talent(name="Big", description="B" * 600)
    huge_talent = Talent(name="Huge", description="H" * 1000)

    small_1 = Talent(name="Small 1", description="S" * 50)
    small_2 = Talent(name="Small 2", description="S" * 50)
    small_3 = Talent(name="Small 3", description="S" * 50)

    tradition = Talent(
        name="Tradycja Niebiańska", description="Dostęp do zaklęć"
    )

    talents = [
        small_talent,
        medium_talent,
        big_talent,
        huge_talent,
        small_1,
        small_2,
        small_3,
        tradition,
    ]

    assigned, overflow = distribute_talents(talents)

    assert "huge_1" in assigned
    assert assigned["huge_1"]["name"] == "Huge"
    assert "big_1" in assigned
    assert assigned["big_1"]["name"] == "Big"
    assert "medium_1" in assigned
    assert assigned["medium_1"]["name"] == "Medium"
    assert "small_1" in assigned
    assert assigned["small_1"]["name"] == "Small"
    assert len(overflow) == 0

    assigned_names = [d["name"] for d in assigned.values()]
    assert "Tradycja Niebiańska" not in assigned_names
    assert len(assigned) == 7

    extra_talents = [
        Talent(name=f"Overflow {i}", description="O" * 1500) for i in range(5)
    ]
    assigned_2, overflow_2 = distribute_talents(extra_talents)
    assert len(overflow_2) == 5
