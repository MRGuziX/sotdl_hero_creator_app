from models.base_hero import AncestryHero
from export.pdf import export_pdf
from pathlib import Path
import pytest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier


def test_export_pdf_delegates_to_existing_renderer(monkeypatch, tmp_path):
    calls = []

    def fake_fill_pdf(hero, output_path):
        calls.append((hero, output_path))
        Path(output_path).write_bytes(b"complete PDF")

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
    assert calls[0][0] == hero
    assert calls[0][0] is not hero
    assert Path(calls[0][1]).parent != destination.parent
    assert destination.read_bytes() == b"complete PDF"
    assert list(tmp_path.iterdir()) == [destination]


def test_failed_export_preserves_previous_file_and_cleans_scratch(monkeypatch, tmp_path, hero):
    destination = tmp_path / "hero.pdf"
    destination.write_bytes(b"previous PDF")

    def fail(hero, path):
        Path(path).write_bytes(b"incomplete")
        Path(path).with_suffix(".overlay.pdf").write_bytes(b"scratch")
        raise RuntimeError("render failed")

    monkeypatch.setattr("export.pdf.fill_pdf", fail)
    with pytest.raises(RuntimeError):
        export_pdf(hero, destination)
    assert destination.read_bytes() == b"previous PDF"
    assert list(tmp_path.iterdir()) == [destination]


def test_concurrent_exports_have_separate_scratch_files(monkeypatch, tmp_path, hero):
    barrier = Barrier(2)
    paths = []

    def render(hero, path):
        paths.append(path)
        Path(path).write_bytes(str(hero.health).encode())
        barrier.wait()

    monkeypatch.setattr("export.pdf.fill_pdf", render)
    other = hero.model_copy(deep=True)
    other.health += 4
    destination = tmp_path / "hero.pdf"
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda item: export_pdf(item, destination), [hero, other]))
    assert len(set(paths)) == 2
    assert destination.read_bytes() in {str(hero.health).encode(), str(other.health).encode()}
    assert list(tmp_path.iterdir()) == [destination]
