import pytest
from pypdf import PdfReader

from export.pdf import export_pdf
from models.spell import Spell
from utils.pdf_creator import fill_spell_pdf


def test_spell_effect_is_below_actual_wrapped_description(hero, tmp_path):
    pymupdf = pytest.importorskip("pymupdf")
    hero.spells = [
        Spell(
            name="Geometria",
            target="Cel: Jedno stworzenie w średnim zasięgu.",
            duration="Koncentracja, do 1 minuty.",
            description="Treść opisu. " * 20,
            critical_success="Koniec efektu.",
        )
    ]
    destination = tmp_path / "spells.pdf"
    fill_spell_pdf(hero, str(destination))
    with pymupdf.open(destination) as document:
        spans = [
            span
            for block in document[0].get_text("dict")["blocks"]
            for line in block.get("lines", [])
            for span in line["spans"]
        ]
    bottom = max(span["bbox"][3] for span in spans if "opisu" in span["text"])
    top = min(span["bbox"][1] for span in spans if "Rzut na atak" in span["text"])
    assert top >= bottom


def test_multi_page_spell_export_keeps_every_card(hero, tmp_path):
    hero.spells = [
        Spell(name=f"Zaklęcie {index}", description="Opis czaru.") for index in range(20)
    ]
    destination = export_pdf(hero, tmp_path / "hero.pdf")
    reader = PdfReader(destination)
    assert len(reader.pages) == 5
    text = " ".join(page.extract_text() for page in reader.pages[2:])
    for index in range(20):
        assert f"Zaklęcie {index}" in text
