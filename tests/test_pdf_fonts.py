import logging

from pypdf import PdfReader
from export.pdf import export_pdf


def test_polish_form_appearances_embed_a_unicode_font(hero, tmp_path, caplog):
    hero.ancestry_name = "Człowiek — Zażółć gęślą jaźń"
    destination = tmp_path / "hero.pdf"
    with caplog.at_level(logging.WARNING):
        export_pdf(hero, destination)
    reader = PdfReader(destination)
    font = reader.trailer["/Root"]["/AcroForm"]["/DR"]["/Font"]["/Athelas"]
    assert font["/Subtype"] == "/Type0"
    assert "/FontFile2" in font["/DescendantFonts"][0]["/FontDescriptor"]
    annotation = next(
        a.get_object() for a in reader.pages[0]["/Annots"] if a.get_object().get("/T") == "ancestry"
    )
    assert annotation["/AP"]["/N"]["/Resources"]["/Font"]["/Athelas"]["/Subtype"] == "/Type0"
    assert reader.trailer["/Root"]["/AcroForm"]["/NeedAppearances"].value is False
    assert not any(
        "encoding" in record.message or "Font dictionary" in record.message
        for record in caplog.records
    )


def test_rendered_polish_text_and_long_notes_are_not_clipped(hero, tmp_path):
    import pytest

    pymupdf = pytest.importorskip("pymupdf")
    hero.ancestry_name = "Człowiek"
    hero.backstory["past"] = "Zażółć gęślą jaźń (test). " * 12
    destination = export_pdf(hero, tmp_path / "hero.pdf")
    with pymupdf.open(destination) as document:
        text = " ".join(document[0].get_text().split())
    assert "Człowiek" in text
    assert text.count("Zażółć gęślą jaźń (test).") == 12
