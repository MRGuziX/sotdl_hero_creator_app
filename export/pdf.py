"""PDF export boundary preserving the existing character-sheet renderer."""

from pathlib import Path

from models.base_hero import AncestryHero
from utils.pdf_creator import fill_pdf


def export_pdf(hero: AncestryHero, output_path: str | Path) -> Path:
    """Render a hero to the existing PDF template and return its path."""
    destination = Path(output_path)
    fill_pdf(hero, str(destination))
    return destination