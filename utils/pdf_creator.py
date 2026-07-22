import json
import pathlib
from dataclasses import dataclass

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import black
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

from models.base_hero import AncestryHero

SPELL_NAME_FONT = "FirstOrderPL"
SPELL_FONT = "Athelas"
SPELL_FONT_BOLD = "Athelas-Bold"


def _register_spell_fonts() -> None:
    fonts_dir = pathlib.Path(__file__).parent.parent / "data_base" / "fonts"
    name_font_path = fonts_dir / "first_order_pl.ttf"
    text_font_path = fonts_dir / "athelas.ttc"
    if not name_font_path.exists() or not text_font_path.exists():
        raise RuntimeError("Nie znaleziono fontów First Order PL lub Athelas.")
    if SPELL_NAME_FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(SPELL_NAME_FONT, str(name_font_path)))
    if SPELL_FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(SPELL_FONT, str(text_font_path), subfontIndex=0))
    if SPELL_FONT_BOLD not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(SPELL_FONT_BOLD, str(text_font_path), subfontIndex=3))


@dataclass
class TalentBox:
    field_id: str
    capacity: int
    name_field: str
    desc_field: str


TALENT_BOX_CONFIG = {
    "maly": {"count": 3, "capacity": 69},
    "sredni": {"count": 7, "capacity": 414},
    "kwadrat": {"count": 2, "capacity": 272},
    "duzy": {"count": 1, "capacity": 912},
    "ogromny": {"count": 1, "capacity": 1774},
}


def get_talent_boxes():
    boxes = []
    for box_type, config in TALENT_BOX_CONFIG.items():
        for i in range(1, config["count"] + 1):
            boxes.append(
                TalentBox(
                    field_id=f"{box_type}_{i}",
                    capacity=config["capacity"],
                    name_field=f"nazwa_talent_{box_type}_{i}",
                    desc_field=f"opis_talent_{box_type}_{i}",
                )
            )

    return sorted(boxes, key=lambda b: b.capacity)


def _talent_box_capacity(description_length):
    """Return the smallest box capacity that can contain a description."""
    match description_length:
        case length if length <= 69:
            return 69
        case length if length <= 272:
            return 272
        case length if length <= 414:
            return 414
        case length if length <= 912:
            return 912
        case length if length <= 1774:
            return 1774
        case _:
            return None


def distribute_talents(talents):
    available_boxes = get_talent_boxes()
    assigned = {}
    overflow = []

    # Place longer talents first so they do not consume boxes needed by smaller talents.
    sorted_talents = sorted(
        (talent for talent in talents if not talent.name.startswith("Tradycja: ")),
        key=lambda talent: len(talent.description or ""),
        reverse=True,
    )

    for talent in sorted_talents:
        description = talent.description or ""
        capacity = _talent_box_capacity(len(description))
        if capacity is None:
            overflow.append(talent)
            continue

        # Within the selected size, use the first empty box. If all are full,
        # continue with the next larger size.
        box = next(
            (candidate for candidate in available_boxes if candidate.capacity >= capacity),
            None,
        )

        if box:
            assigned[box.field_id] = {
                "name": talent.name,
                "description": description,
                "box": box,
            }
            available_boxes.remove(box)
        else:
            overflow.append(talent)

    return assigned, overflow


def fill_pdf(hero: AncestryHero, output_path: str) -> None:
    """Fill the bundled character-sheet template and write it to `output_path`.

    The hero is read but not mutated. The destination directory must be writable;
    PDF and filesystem errors are propagated to the caller.
    """
    project_root = pathlib.Path(__file__).parent.parent
    template_path = project_root / "data_base" / "card_no_color.pdf"

    reader = PdfReader(template_path)
    writer = PdfWriter()
    writer.append(reader)

    # 1. Distribute talents into boxes on Page 2
    assigned_talents, overflow_talents = distribute_talents(hero.talents)

    # 2. Prepare all fields
    path_name = hero.path_name or ""
    if path_name:
        path_file = project_root / "data_base" / "paths" / "novice" / f"{path_name.lower()}.json"
        if path_file.exists():
            path_name = json.loads(path_file.read_text(encoding="utf-8")).get(
                "path_name", path_name
            )

    fields = {
        "sila": str(hero.strength),
        "wola": str(hero.will),
        "intelekt": str(hero.intelligence),
        "zrecznosc": str(hero.dexterity),
        "sila_mod": str(hero.strength - 10),
        "wola_mod": str(hero.will - 10),
        "intelekt_mod": str(hero.intelligence - 10),
        "zrecznosc_mod": str(hero.dexterity - 10),
        "percepcja": str(hero.perception),
        "obrona": str(hero.defense),
        "zdrowie": str(hero.health),
        "predkosc": str(hero.speed),
        "moc": str(hero.power),
        "obrazenia": str(hero.damage),
        "szalenstwo": str(hero.insanity),
        "splugawienie": str(hero.corruption),
        "szybkosc_zdrowienia": str(hero.health // 4),
        "rozmiar": str(hero.size[0]) if hero.size else "1",
        "pochodzenie": hero.ancestry_name,
        "nowicjusz": path_name,
        "poziom": str(hero.level),
        "okrawki": str(hero.money.okrawki) if hero.money.okrawki else "",
        "miedziaki": str(hero.money.miedziaki) if hero.money.miedziaki else "",
        "srebro": str(hero.money.srebrniki) if hero.money.srebrniki else "",
        "zloto": str(hero.money.zlote_korony) if hero.money.zlote_korony else "",
        "plecak": ", ".join(hero.equipment.backpack) if hero.equipment.backpack else "",
        "wyglad": " ".join(
            filter(
                None,
                [
                    hero.backstory.get("appearance", ""),
                    hero.backstory.get("body", ""),
                    hero.backstory.get("age", ""),
                    hero.backstory.get("form", ""),
                ],
            )
        ),
        "osobowosc": hero.backstory.get("personality", ""),
        "zamoznosc": hero.wealth.split(":")[0] if hero.wealth else "",
    }

    # Add assigned talents to Page 2 fields
    for box_id, data in assigned_talents.items():
        box = data["box"]
        fields[box.name_field] = data["name"]
        fields[box.desc_field] = data["description"]

    # 3. Build 'notatki' for Page 1 (including overflow talents and spells)
    notatki_parts = []
    if hero.backstory.get("past"):
        notatki_parts.append(hero.backstory["past"])
        notatki_parts.append("")
    if hero.backstory.get("religion"):
        notatki_parts.append(hero.backstory["religion"])
        notatki_parts.append("")

    if hero.languages:
        lang_written = [language.name for language in hero.languages if language.can_write]
        lang_spoken = [language.name for language in hero.languages if not language.can_write]
        if lang_spoken:
            notatki_parts.append(f"Języki znane: {', '.join(lang_spoken)}")
        if lang_written:
            notatki_parts.append(f"Języki pisane: {', '.join(lang_written)}")
        notatki_parts.append("")

    if hero.professions:
        notatki_parts.append(f"Profesje: {', '.join(hero.professions)}")
        notatki_parts.append("")

    if overflow_talents:
        notatki_parts.append("TALENTY (NADMIAROWE):")
        for t in overflow_talents:
            desc = f": {t.description}" if t.description else ""
            notatki_parts.append(f"• {t.name}{desc}")
        notatki_parts.append("")

    if hero.oddity:
        notatki_parts.append(f"Kuriozum: {hero.oddity}")

    # Spells are skipped for now - we need other pdf for that
    # if hero.spells:
    #     notatki_parts.append("CZARY:")
    #     for s in hero.spells:
    #         desc = f": {s.description}" if s.description else ""
    #         notatki_parts.append(f"• {s.name} (Poz. {s.level}){desc}")
    #     notatki_parts.append("")

    fields["notatki"] = "\n".join(notatki_parts)

    for i, weapon in enumerate(hero.equipment.weapons[:5]):
        fields[f"ekwipunek_{i + 1}"] = weapon.name
        fields[f"obrazenia_{i + 1}"] = weapon.damage
        fields[f"cechy_{i + 1}"] = weapon.properties

    # Update Page 1
    writer.update_page_form_field_values(writer.pages[0], fields)
    # Update Page 2 (pypdf will ignore fields that don't exist on this page)
    if len(writer.pages) > 1:
        writer.update_page_form_field_values(writer.pages[1], fields)

    with open(output_path, "wb") as output_stream:
        writer.write(output_stream)
    return output_path


def _draw_wrapped_text(
    canvas: Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    font_size: int,
    leading: float | None = None,
) -> float:
    style = ParagraphStyle(
        "spell_text",
        fontName=SPELL_FONT,
        fontSize=font_size,
        leading=leading or font_size * 1.2,
        textColor=black,
        alignment=TA_LEFT,
    )
    paragraph = Paragraph(text.replace("&", "&amp;"), style)
    _, height = paragraph.wrap(width, A4[1])
    paragraph.drawOn(canvas, x, y - height)
    return height


def _spell_name_font_size(name: str) -> int:
    name_length = len(name)
    if name_length <= 12:
        return 18
    if name_length <= 23:
        return 14
    return 12


def fill_spell_pdf(hero: AncestryHero, output_path: str) -> str:
    """Create one spell card per known spell using ``spell_card_v1.pdf`` as a background."""
    template_path = pathlib.Path(__file__).parent.parent / "data_base" / "spell_card_v1.pdf"
    if not hero.spells:
        raise ValueError("Nie można utworzyć kart zaklęć bez zaklęć.")

    _register_spell_fonts()
    overlay_path = pathlib.Path(output_path).with_suffix(".spell-overlay.pdf")
    canvas = Canvas(str(overlay_path), pagesize=A4)
    for spell in hero.spells:
        canvas.setFont(SPELL_NAME_FONT, _spell_name_font_size(spell.name))
        canvas.drawCentredString(A4[0] / 2, A4[1] - 38 * mm, spell.name)
        canvas.setFont(SPELL_FONT, 11)
        canvas.drawString(35 * mm, A4[1] - 58 * mm, f"Poziom: {spell.level}")
        y = A4[1] - 76 * mm
        for label, value in (
            ("Cel", spell.target),
            ("Obszar", spell.area),
            ("Czas trwania", spell.duration),
        ):
            if value:
                canvas.setFont(SPELL_FONT_BOLD, 11)
                canvas.drawString(35 * mm, y, f"{label}:")
                canvas.setFont(SPELL_FONT, 11)
                y -= _draw_wrapped_text(canvas, value, 35 * mm + 24 * mm, y + 4, 125 * mm, 11)
                y -= 4
        y -= 4
        canvas.setFont(SPELL_FONT_BOLD, 11)
        canvas.drawString(35 * mm, y, "Opis:")
        y -= 5
        description_size = 9 if len(spell.description) > 250 else 11
        y -= _draw_wrapped_text(canvas, spell.description, 35 * mm, y, 145 * mm, description_size)
        if spell.critical_success:
            y -= 10
            canvas.setFont(SPELL_FONT_BOLD, 11)
            critical_prefix = "Rzut na atak 20+:"
            critical_text = spell.critical_success
            if critical_text.startswith(critical_prefix):
                critical_text = critical_text[len(critical_prefix) :].lstrip()
            canvas.drawString(35 * mm, y, critical_prefix)
            y -= 5
            y -= _draw_wrapped_text(canvas, critical_text, 35 * mm, y, 145 * mm, 11)
        if spell.tags:
            y -= 10
            canvas.setFont(SPELL_FONT_BOLD, 11)
            canvas.drawString(35 * mm, y, "Tagi:")
            y -= 5
            _draw_wrapped_text(canvas, ", ".join(spell.tags), 35 * mm, y, 145 * mm, 11)
        canvas.showPage()
    canvas.save()

    background = PdfReader(template_path)
    overlay = PdfReader(overlay_path)
    writer = PdfWriter()
    for page in overlay.pages:
        card = background.pages[0]
        card.merge_page(page)
        writer.add_page(card)
    with open(output_path, "wb") as output_stream:
        writer.write(output_stream)
    overlay_path.unlink()
    return output_path
