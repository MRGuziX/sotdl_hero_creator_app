"""PDF export boundary preserving the existing character-sheet renderer."""

from pathlib import Path
import os
from tempfile import TemporaryDirectory

from models.base_hero import AncestryHero
from utils.pdf_creator import fill_pdf


def export_pdf(hero: AncestryHero, output_path: str | Path) -> Path:
    """Render a hero to the existing PDF template and return its path."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="sotdl-export-", dir=destination.parent) as scratch:
        temporary = Path(scratch) / "hero.pdf"
        fill_pdf(hero.model_copy(deep=True), str(temporary))
        os.replace(temporary, destination)
    return destination
