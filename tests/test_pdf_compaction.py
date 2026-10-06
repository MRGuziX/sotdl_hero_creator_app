from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from utils.pdf_creator import _compress_pdf


def test_spell_template_compaction_keeps_identical_pixels_without_editor_metadata():
    pymupdf = pytest.importorskip("pymupdf")

    template = Path(__file__).resolve().parent.parent / "data_base/spell_card_no_color.pdf"
    reader = PdfReader(template)
    original = template.read_bytes()
    writer = PdfWriter()
    writer.add_page(reader.pages[0], excluded_keys=["/PieceInfo"])
    _compress_pdf(writer)
    output = BytesIO()
    writer.write(output)
    compact = output.getvalue()
    assert len(compact) < len(original)
    assert "/PieceInfo" not in PdfReader(BytesIO(compact)).pages[0]
    with pymupdf.open(stream=original, filetype="pdf") as source:
        before = source[0].get_pixmap(matrix=pymupdf.Matrix(0.5, 0.5)).samples
    with pymupdf.open(stream=compact, filetype="pdf") as optimized:
        after = optimized[0].get_pixmap(matrix=pymupdf.Matrix(0.5, 0.5)).samples
    assert after == before
