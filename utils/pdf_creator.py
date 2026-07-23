import json
import pathlib
from dataclasses import dataclass

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import black
from reportlab.lib.enums import TA_CENTER, TA_LEFT
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


def _spell_description_layout(description: str) -> tuple[int, str]:
    """Return the description font size and the single card template name."""
    return (8 if len(description or "") <= 500 else 7), "empty_spell_cards"


def _spell_description_font_size(description: str) -> int:
    return _spell_description_layout(description)[0]


def _spell_card_fields(spell, card_number: int) -> dict[str, str]:
    """Build the numbered field dictionary used by the 3x3 card loop."""
    return {
        f"spell_name_card_{card_number}": spell.name or "",
        f"spell_target_card_{card_number}": spell.target or "",
        f"spell_duration_card_{card_number}": spell.duration or "",
        f"spell_area_card_{card_number}": spell.area or "",
        f"spell_description_card_{card_number}": spell.description or "",
        f"spell_attack_roll_card_{card_number}": spell.critical_success or "",
        f"spell_tags_card_{card_number}": ", ".join(spell.tags or []),
    }


def _spell_description_bounds(column_px: float) -> tuple[float, float]:
    """Return the left edge and width of a card's description area in pixels."""
    first_column = 488
    left_edge = 170
    right_edge = 798
    column_step = column_px - first_column
    return left_edge + column_step, right_edge - left_edge


def _spell_name_bounds(column_px: float) -> tuple[float, float]:
    """Return the original name area, independent of the description area."""
    first_column = 488
    left_edge = 170
    right_edge = 800
    column_step = column_px - first_column
    return left_edge + column_step, right_edge - left_edge


def _draw_wrapped_centered(
    canvas: Canvas,
    text: str,
    left: float,
    top: float,
    width: float,
    font_name: str,
    font_size: int,
    px_to_x: float,
    px_to_y: float,
) -> float:
    style = ParagraphStyle(
        "spell_name",
        fontName=font_name,
        fontSize=font_size,
        leading=font_size * 1.2,
        textColor=black,
        alignment=TA_CENTER,
    )
    paragraph = Paragraph(text.replace("&", "&amp;"), style)
    _, height = paragraph.wrap(width * px_to_x, A4[1])
    paragraph.drawOn(canvas, left * px_to_x, A4[1] - top * px_to_y - height)
    return height


def fill_spell_pdf(hero: AncestryHero, output_path: str) -> str:
    """Render up to nine spells per page on the 3x3 card template."""
    templates_dir = pathlib.Path(__file__).parent.parent / "data_base"
    template_path = templates_dir / "empty_spell_cards.pdf"
    output_file = pathlib.Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    if not hero.spells:
        raise ValueError("Nie można utworzyć kart zaklęć bez zaklęć.")

    _register_spell_fonts()
    overlay_path = output_file.with_suffix(".spell-overlay.pdf")
    canvas = Canvas(str(overlay_path), pagesize=A4)
    px_to_x = A4[0] / 2480
    px_to_y = A4[1] / 3508
    columns = (488, 1249, 1991)
    row_bases = (140, 1332, 2435)

    def draw_centered(
        text: str, x_px: float, y_px: float, size: int, font_name: str = SPELL_FONT
    ) -> None:
        canvas.setFont(font_name, size)
        canvas.drawCentredString(x_px * px_to_x, A4[1] - y_px * px_to_y, text)

    for page_start in range(0, len(hero.spells), 9):
        for card_index, spell in enumerate(hero.spells[page_start : page_start + 9], 1):
            column = columns[(card_index - 1) % 3]
            base_y = row_bases[(card_index - 1) // 3]
            fields = _spell_card_fields(spell, card_index)
            description = fields[f"spell_description_card_{card_index}"]
            description_size, _ = _spell_description_layout(description)
            name = fields[f"spell_name_card_{card_index}"]
            name_left, name_width = _spell_name_bounds(column)
            _draw_wrapped_centered(
                canvas,
                name,
                name_left,
                base_y,
                name_width,
                SPELL_NAME_FONT,
                _spell_name_font_size(name),
                px_to_x,
                px_to_y,
            )
            for offset, field_name in ((175, "target"), (205, "duration"), (235, "area")):
                value = fields[f"spell_{field_name}_card_{card_index}"]
                if value:
                    draw_centered(str(value), column, base_y + offset, 7)
            style = ParagraphStyle(
                "spell_card",
                fontName=SPELL_FONT,
                fontSize=description_size,
                leading=description_size * 1.2,
                textColor=black,
                alignment=TA_CENTER,
            )
            paragraph = Paragraph(description.replace("&", "&amp;"), style)
            description_left, description_width = _spell_description_bounds(column)
            width = description_width * px_to_x
            _, height = paragraph.wrap(width, 500 * px_to_y)
            paragraph.drawOn(
                canvas,
                description_left * px_to_x,
                A4[1] - (base_y + 355) * px_to_y - height,
            )
            if fields[f"spell_attack_roll_card_{card_index}"]:
                critical = (
                    fields[f"spell_attack_roll_card_{card_index}"]
                    .removeprefix("Rzut na atak 20+:")
                    .strip()
                )
                draw_centered(f"rzut na atak 20+: {critical}", column, base_y + 400, 7)
            if fields[f"spell_tags_card_{card_index}"]:
                draw_centered(fields[f"spell_tags_card_{card_index}"], column, base_y + 940, 7)
        canvas.showPage()
    canvas.save()

    overlay = PdfReader(overlay_path)
    writer = PdfWriter()
    for page in overlay.pages:
        card = PdfReader(template_path).pages[0]
        card.merge_page(page)
        writer.add_page(card)
    with output_file.open("wb") as output_stream:
        writer.write(output_stream)
    overlay_path.unlink()
    return output_path
