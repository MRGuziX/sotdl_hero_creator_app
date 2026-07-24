from models.base_hero import AncestryHero
from export.pdf import export_pdf


def test_export_pdf_delegates_to_existing_renderer(monkeypatch, tmp_path):
    calls = []

    def fake_fill_pdf(hero, output_path):
        calls.append((hero, output_path))

    monkeypatch.setattr("export.pdf.fill_pdf", fake_fill_pdf)
    hero = AncestryHero(
        ancestry_name="Człowiek",
        strength=10,
        dexterity=10,
        intelligence=10,
        will=10,
        perception=10,
        defense=10,
        health=10,
        healing_rate=1,
        size=[1.0, 1.0],
        speed=10,
    )
    destination = tmp_path / "hero.pdf"

    result = export_pdf(hero, destination)

    assert result == destination
    assert calls == [(hero, str(destination))]