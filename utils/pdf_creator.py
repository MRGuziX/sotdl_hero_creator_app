import json
import pathlib
import re
from dataclasses import dataclass
from html import escape
from typing import Any

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, create_string_object
from reportlab.lib.colors import black, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from models.base_hero import AncestryHero

SPELL_NAME_FONT = "FirstOrderPL"
SPELL_FONT = "Athelas"
SPELL_FONT_BOLD = "Athelas-Bold"

# Spell-card coordinate system, expressed in the template's pixel grid.
SPELL_CARD_COLUMNS_X = (500, 1253, 2007)
SPELL_CARD_ROW_BASES_Y = (135, 1255, 2375)

SPELL_NAME_LEFT_X = 170
SPELL_NAME_RIGHT_X = 800
SPELL_DESCRIPTION_LEFT_X = 170
SPELL_DESCRIPTION_RIGHT_X = 798

SPELL_TECHNICAL_FIELDS_OFFSET_Y = 155
SPELL_TECHNICAL_FIELD_GAP_PX = 10
SPELL_DESCRIPTION_OFFSET_Y = 335
SPELL_DESCRIPTION_GAP_AFTER_TECHNICAL_PX = 50
SPELL_TABLE_GAP_AFTER_DESCRIPTION_PX = 25
SPELL_CRITICAL_SUCCESS_GAP_PX = 0
SPELL_TAGS_OFFSET_Y = 1000
SPELL_ORIGIN_LEFT_OFFSET_X = 335
SPELL_ORIGIN_FIRST_ROW_OFFSET_Y = 980
SPELL_ORIGIN_SECOND_ROW_OFFSET_Y = 970
SPELL_ORIGIN_THIRD_ROW_OFFSET_Y = 960
SPELL_ORIGIN_FONT_SIZE = 8
SPELL_TABLE_FONT_SIZE = 5


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
    "small": {"count": 8, "capacity": 160},
    "medium": {"count": 8, "capacity": 470},
    "big": {"count": 4, "capacity": 760},
    "huge": {"count": 2, "capacity": 1070},
}


def get_talent_boxes():
    boxes = []
    for box_type, config in TALENT_BOX_CONFIG.items():
        for i in range(1, config["count"] + 1):
            boxes.append(
                TalentBox(
                    field_id=f"{box_type}_{i}",
                    capacity=config["capacity"],
                    name_field=f"name_{box_type}_{i}",
                    desc_field=f"description_{box_type}_{i}",
                )
            )

    return sorted(boxes, key=lambda b: b.capacity)


def _talent_box_capacity(description_length):
    """Return the smallest box capacity that can contain a description."""
    match description_length:
        case length if length <= 160:
            return 160
        case length if length <= 470:
            return 470
        case length if length <= 760:
            return 760
        case length if length <= 1070:
            return 1070
        case _:
            return None


def distribute_talents(talents):
    available_boxes = get_talent_boxes()
    assigned = {}
    overflow = []

    # Place longer talents first so they do not consume boxes needed by smaller talents.
    sorted_talents = sorted(
        (talent for talent in talents if not talent.name.startswith("Tradycja ")),
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


def _propagate_parent_values(writer: PdfWriter) -> None:
    """Copy /V from parent field objects to their widget annotations.

    Some fields in the PDF templates use a parent-child structure where the
    field name and value live on a parent dictionary while the visible widget
    is a child with an empty /V.  pypdf's update_page_form_field_values sets
    /NeedAppearances=True so viewers regenerate appearances from /V, but
    certain viewers (macOS Preview, some Acrobat versions) only inspect the
    widget's own /V — not the parent's — and render blank fields.  Copying
    the value down to each widget ensures every viewer finds it.
    """
    for page in writer.pages:
        for annot in page.get("/Annots", []):
            obj = annot.get_object()
            parent = obj.get("/Parent")
            if parent is None:
                continue
            parent_obj = parent.get_object() if hasattr(parent, "get_object") else parent
            parent_v = parent_obj.get("/V")
            if parent_v and not obj.get("/V"):
                obj[NameObject("/V")] = create_string_object(str(parent_v))


def fill_pdf(hero: AncestryHero, output_path: str) -> None:
    """Fill the bundled character-sheet template and write it to `output_path`.

    The hero is read but not mutated. The destination directory must be writable;
    PDF and filesystem errors are propagated to the caller.
    """
    project_root = pathlib.Path(__file__).parent.parent
    hero_template = project_root / "data_base" / "hero_card_no_color.pdf"
    talent_template = project_root / "data_base" / "talent_card_no_color.pdf"

    writer = PdfWriter()
    writer.append(PdfReader(hero_template))
    writer.append(PdfReader(talent_template))

    assigned_talents, overflow_talents = distribute_talents(hero.talents)

    def _get_path_display_name(tier, path_id):
        if not path_id:
            return ""
        path_file = project_root / "data_base" / "paths" / tier / f"{path_id.lower()}.json"
        if path_file.exists():
            try:
                data = json.loads(path_file.read_text(encoding="utf-8"))
                return data.get("path_name", path_id)
            except Exception:
                return path_id
        return path_id

    novice_path = _get_path_display_name("novice", hero.path_name)
    expert_path = ", ".join([_get_path_display_name("expert", p) for p in hero.expert_path_names])
    master_path = _get_path_display_name("master", hero.master_path_name)

    hero_fields = {
        "strength": str(hero.strength),
        "will": str(hero.will),
        "inteligence": str(hero.intelligence),
        "dexterity": str(hero.dexterity),
        "str_mod": str(hero.strength - 10),
        "will_mod": str(hero.will - 10),
        "int_mod": str(hero.intelligence - 10),
        "dex_mod": str(hero.dexterity - 10),
        "perception": str(hero.perception),
        "defence": str(hero.defense),
        "health": str(hero.health),
        "speed": str(hero.speed),
        "power": str(hero.power),
        "damage": str(hero.damage),
        "insanity": str(hero.insanity),
        "corruption": str(hero.corruption),
        "healing_rate": str(hero.health // 4),
        "size": str(hero.size[0]) if hero.size else "1",
        "ancestry": hero.ancestry_name,
        "novice": novice_path,
        "expert": expert_path,
        "master": master_path,
        "level": str(hero.level),
        "bits": str(hero.money.okrawki) if hero.money.okrawki else "",
        "copper": str(hero.money.miedziaki) if hero.money.miedziaki else "",
        "silver": str(hero.money.srebrniki) if hero.money.srebrniki else "",
        "gold": str(hero.money.zlote_korony) if hero.money.zlote_korony else "",
        "backpack": ", ".join(hero.equipment.backpack),
        "armor": hero.equipment.armors[0].name if hero.equipment.armors else "",
        "shield": hero.equipment.shields[0].name if hero.equipment.shields else "",
        "look": " ".join(
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
        "character": hero.backstory.get("personality", ""),
        "wealth": hero.wealth.split(":")[0] if hero.wealth else "",
    }

    notes_parts = []
    if hero.backstory.get("past"):
        notes_parts.append(hero.backstory["past"])
        notes_parts.append("")
    if hero.backstory.get("religion"):
        notes_parts.append(hero.backstory["religion"])
        notes_parts.append("")

    if hero.languages:
        lang_written = [language.name for language in hero.languages if language.can_write]
        lang_spoken = [language.name for language in hero.languages if not language.can_write]
        if lang_spoken:
            notes_parts.append(f"Języki znane: {', '.join(lang_spoken)}")
        if lang_written:
            notes_parts.append(f"Języki pisane: {', '.join(lang_written)}")
        notes_parts.append("")

    if hero.professions:
        notes_parts.append(f"Profesje: {', '.join(hero.professions)}")
        notes_parts.append("")

    traditions = sorted(
        talent.name for talent in hero.talents if talent.name.startswith("Tradycja ")
    )
    if traditions:
        notes_parts.append(f"Tradycje magiczne: {', '.join(traditions)}")
        notes_parts.append("")

    if overflow_talents:
        notes_parts.append("TALENTY (NADMIAROWE):")
        for t in overflow_talents:
            desc = f": {t.description}" if t.description else ""
            notes_parts.append(f"• {t.name}{desc}")
        notes_parts.append("")

    if hero.oddity:
        notes_parts.append(f"Kuriozum: {hero.oddity}")

    hero_fields["notes"] = "\n".join(notes_parts)

    for i, weapon in enumerate(hero.equipment.weapons[:5]):
        hero_fields[f"weapon_{i + 1}"] = weapon.name
        hero_fields[f"dmg_{i + 1}"] = weapon.damage
        if i + 1 != 2:
            hero_fields[f"property_{i + 1}"] = weapon.properties

    talent_fields = {}
    for box_id, data in assigned_talents.items():
        box = data["box"]
        talent_fields[box.name_field] = data["name"]
        talent_fields[box.desc_field] = data["description"]

    writer.update_page_form_field_values(writer.pages[0], hero_fields)
    writer.update_page_form_field_values(writer.pages[1], talent_fields)
    _propagate_parent_values(writer)

    renderable_spells = [
        spell
        for spell in hero.spells
        if spell.name not in {"any", "known_tradition"} and spell.description != "Nowe zaklęcie"
    ]
    if renderable_spells:
        spell_output_path = pathlib.Path(output_path).with_suffix(".spell-pages.pdf")
        fill_spell_pdf(hero, str(spell_output_path))
        spell_reader = PdfReader(spell_output_path)
        for spell_page in spell_reader.pages:
            writer.add_page(spell_page)
        spell_output_path.unlink()

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
        return 16
    if name_length <= 23:
        return 14
    return 12


def _spell_description_layout(description: str) -> tuple[int, str]:
    """Return the description font size and the single card template name."""
    letters = len(description)
    if letters <= 500:
        return 8, "empty_spell_cards"
    elif letters <= 700:
        return 7, "empty_spell_cards"
    else:
        return 6, "empty_spell_cards"


def _spell_description_font_size(description: str) -> int:
    return _spell_description_layout(description)[0]


def _spell_card_fields(spell, card_number: int) -> dict[str | Any, str | dict[Any, Any] | Any]:
    """Build the numbered field dictionary used by the 3x3 card loop."""
    return {
        f"spell_name_card_{card_number}": spell.name or "",
        f"spell_target_card_{card_number}": spell.target or "",
        f"spell_duration_card_{card_number}": spell.duration or "",
        f"spell_area_card_{card_number}": spell.area or "",
        f"spell_description_card_{card_number}": (
                spell.card_description or spell.description or ""
        ),
        f"spell_attack_roll_card_{card_number}": spell.critical_success or "",
        f"spell_requirements_card_{card_number}": spell.requirements or "",
        f"spell_sacrifice_card_{card_number}": spell.sacrifice or "",
        f"spell_permanent_card_{card_number}": spell.permanent or "",
        f"spell_table_card_{card_number}": spell.table or {},
        f"spell_origin_card_{card_number}": spell.origin or {},
        f"spell_tags_card_{card_number}": (
            f"{', '.join(spell.tags or [])} {spell.level}" if spell.tags else str(spell.level)
        ),
    }


def _draw_spell_table(
        canvas: Canvas,
        table_data: dict,
        left: float,
        top: float,
        width: float,
        px_to_x: float,
        px_to_y: float,
) -> float:
    """Draw a spell table stored as {headers: [...], rows: [[...], ...]}.

    The table is intentionally data-only, so it can be loaded directly from JSON.
    """
    headers = table_data.get("headers", [])
    rows = table_data.get("rows", [])
    if not headers or not rows:
        return 0
    table_width = width * px_to_x
    column_widths = _spell_table_column_widths(headers, table_width)
    cell_style = ParagraphStyle(
        "spell_table_cell",
        fontName=SPELL_FONT,
        fontSize=SPELL_TABLE_FONT_SIZE,
        leading=7,
        textColor=black,
        alignment=TA_CENTER,
    )
    header_style = ParagraphStyle(
        "spell_table_header",
        parent=cell_style,
        fontName=SPELL_FONT_BOLD,
        textColor=white,
    )
    column_count = len(headers)
    normalized_rows = [list(row[:column_count]) for row in rows]
    normalized_rows = [row + [""] * (column_count - len(row)) for row in normalized_rows]
    data = [[Paragraph(escape(str(value)), header_style) for value in headers]]
    data.extend(
        [[Paragraph(escape(str(value)), cell_style) for value in row] for row in normalized_rows]
    )
    table = Table(data, colWidths=column_widths, hAlign="CENTER")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), black),
                ("TEXTCOLOR", (0, 0), (-1, 0), white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, black),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    _, height = table.wrap(table_width, A4[1])
    table.drawOn(canvas, left * px_to_x, A4[1] - top * px_to_y - height)
    return height


def _spell_table_column_widths(headers: list, table_width: float) -> list[float]:
    """Return widths that keep headers on one line and use the remaining space."""
    _register_spell_fonts()
    header_padding = 8
    minimum_widths = [
        pdfmetrics.stringWidth(str(header), SPELL_FONT_BOLD, SPELL_TABLE_FONT_SIZE) + header_padding
        for header in headers
    ]
    minimum_total = sum(minimum_widths)
    if minimum_total >= table_width:
        scale = table_width / minimum_total
        return [width * scale for width in minimum_widths]

    remaining = table_width - minimum_total
    weights = [1 / len(headers)] * len(headers)
    if len(headers) == 2:
        weights = [0.2, 0.8]
    return [minimum + remaining * weight for minimum, weight in zip(minimum_widths, weights)]


def _spell_origin_text(origin: dict) -> str:
    """Format the book and page shown in the card's lower-left corner."""
    if not origin:
        return ""
    source = str(origin.get("source", "")).strip()
    number = origin.get("number")
    if not source and number is None:
        return ""
    return f"{source} {number}".strip()


def _spell_origin_x(column_px: float) -> float:
    """Return the origin footer X position using one offset for every card column."""
    return column_px - SPELL_ORIGIN_LEFT_OFFSET_X


def _spell_origin_offset_y(row_index: int) -> float:
    """Return the configurable origin footer offset for a zero-based card row."""
    offsets = (
        SPELL_ORIGIN_FIRST_ROW_OFFSET_Y,
        SPELL_ORIGIN_SECOND_ROW_OFFSET_Y,
        SPELL_ORIGIN_THIRD_ROW_OFFSET_Y,
    )
    return offsets[row_index]


def _spell_description_bounds(column_px: float) -> tuple[float, float]:
    """Return the left edge and width of a card's description area in pixels."""
    column_step = column_px - SPELL_CARD_COLUMNS_X[0]
    return (
        SPELL_DESCRIPTION_LEFT_X + column_step,
        SPELL_DESCRIPTION_RIGHT_X - SPELL_DESCRIPTION_LEFT_X,
    )


def _spell_name_bounds(column_px: float) -> tuple[float, float]:
    """Return the original name area, independent of the description area."""
    column_step = column_px - SPELL_CARD_COLUMNS_X[0]
    return SPELL_NAME_LEFT_X + column_step, SPELL_NAME_RIGHT_X - SPELL_NAME_LEFT_X


def _spell_critical_success_y(base_y: float, description_height: float, px_to_y: float) -> float:
    """Return the Y position 50 pixels below the wrapped description."""
    return (
            base_y
            + SPELL_DESCRIPTION_OFFSET_Y
            + description_height / px_to_y
            + SPELL_CRITICAL_SUCCESS_GAP_PX
    )


def _spell_description_top(
        base_y: float,
        technical_fields_bottom: float | None,
) -> float:
    """Return the description top 50 px below the last technical field."""
    if technical_fields_bottom is None:
        return base_y + SPELL_DESCRIPTION_OFFSET_Y
    return technical_fields_bottom + SPELL_DESCRIPTION_GAP_AFTER_TECHNICAL_PX


def _spell_table_top(description_top: float, description_height: float, px_to_y: float) -> float:
    """Return the table top 25 px below the wrapped description."""
    return description_top + description_height / px_to_y + SPELL_TABLE_GAP_AFTER_DESCRIPTION_PX


def _spell_effect_value(value: str, label: str) -> str:
    """Remove a card label already present in a technical effect value."""
    prefixes = (label, "Rzut na atak to 20+:") if label == "Rzut na atak 20+:" else (label,)
    for prefix in prefixes:
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return value


def _format_spell_description(text: str) -> str:
    """Format bullets and the ``Reakcja:`` section for a ReportLab paragraph."""
    escaped = text.replace("&", "&amp;")
    formatted = re.sub(r"(?<!^)\s*•", "<br/>•", escaped)
    reaction_label = f'<font name="{SPELL_FONT_BOLD}">Reakcja:</font>'
    formatted = re.sub(r"(?<!^)\s*Reakcja:\s*", f"<br/>{reaction_label} ", formatted)
    return re.sub(r"^Reakcja:\s*", f"{reaction_label} ", formatted)


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
    paragraph = Paragraph(_format_spell_description(text), style)
    _, height = paragraph.wrap(width * px_to_x, A4[1])
    paragraph.drawOn(canvas, left * px_to_x, A4[1] - top * px_to_y - height)
    return height


def _draw_spell_field(
        canvas: Canvas,
        text: str,
        column: float,
        top: float,
        px_to_x: float,
        px_to_y: float,
) -> float:
    """Draw a centered, wrapped technical field and return its height in points."""
    left, width = _spell_description_bounds(column)
    labels = ("Czas działania:", "Czas trwania:", "Cel:", "Obszar:")
    label = next((item for item in labels if text.startswith(item)), "")
    if label:
        text = f'<font name="{SPELL_FONT_BOLD}">{escape(label)}</font>{escape(text[len(label):])}'
    else:
        text = escape(text)
    return _draw_wrapped_centered(
        canvas,
        text,
        left,
        top,
        width,
        SPELL_FONT,
        6,
        px_to_x,
        px_to_y,
    )


def fill_spell_pdf(hero: AncestryHero, output_path: str) -> str:
    """Render up to nine spells per page on the 3x3 card template."""
    templates_dir = pathlib.Path(__file__).parent.parent / "data_base"
    template_path = templates_dir / "spell_card_no_color.pdf"
    output_file = pathlib.Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    spells = [
        spell
        for spell in hero.spells
        if spell.name not in {"any", "known_tradition"} and spell.description != "Nowe zaklęcie"
    ]
    if not spells:
        raise ValueError("Nie można utworzyć kart zaklęć bez zaklęć.")

    _register_spell_fonts()
    overlay_path = output_file.with_suffix(".spell-overlay.pdf")
    canvas = Canvas(str(overlay_path), pagesize=A4)
    px_to_x = A4[0] / 2480
    px_to_y = A4[1] / 3508

    def draw_centered(
            text: str, x_px: float, y_px: float, size: int, font_name: str = SPELL_FONT
    ) -> None:
        canvas.setFont(font_name, size)
        canvas.drawCentredString(x_px * px_to_x, A4[1] - y_px * px_to_y, text)

    for page_start in range(0, len(spells), 9):
        for card_index, spell in enumerate(spells[page_start: page_start + 9], 1):
            column = SPELL_CARD_COLUMNS_X[(card_index - 1) % 3]
            base_y = SPELL_CARD_ROW_BASES_Y[(card_index - 1) // 3]
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
            field_top = base_y + SPELL_TECHNICAL_FIELDS_OFFSET_Y
            last_technical_field_bottom = None
            for field_name in ("target", "duration", "area"):
                value = fields[f"spell_{field_name}_card_{card_index}"]
                if value:
                    field_height = _draw_spell_field(
                        canvas,
                        str(value),
                        column,
                        field_top,
                        px_to_x,
                        px_to_y,
                    )
                    last_technical_field_bottom = field_top + field_height / px_to_y
                    field_top += field_height / px_to_y + SPELL_TECHNICAL_FIELD_GAP_PX
            description_top = _spell_description_top(
                base_y,
                last_technical_field_bottom,
            )
            style = ParagraphStyle(
                "spell_card",
                fontName=SPELL_FONT,
                fontSize=description_size,
                leading=description_size * 1.2,
                textColor=black,
                alignment=TA_CENTER,
            )
            paragraph = Paragraph(_format_spell_description(description), style)
            description_left, description_width = _spell_description_bounds(column)
            width = description_width * px_to_x
            _, height = paragraph.wrap(width, 500 * px_to_y)
            paragraph.drawOn(
                canvas,
                description_left * px_to_x,
                A4[1] - description_top * px_to_y - height,
            )
            table_data = fields[f"spell_table_card_{card_index}"]
            if table_data:
                table_top = _spell_table_top(description_top, height, px_to_y)
                table_height = _draw_spell_table(
                    canvas,
                    table_data,
                    description_left,
                    table_top,
                    description_width,
                    px_to_x,
                    px_to_y,
                )
                effect_y = table_top + table_height / px_to_y + SPELL_TECHNICAL_FIELD_GAP_PX
            else:
                effect_y = _spell_critical_success_y(base_y, height, px_to_y) - 20
            effect_fields = (
                ("spell_attack_roll_card_", "Rzut na atak 20+:"),
                ("spell_requirements_card_", "Wymagania:"),
                ("spell_sacrifice_card_", "Poświęcenie:"),
                ("spell_permanent_card_", "Permanentny efekt:"),
            )
            left, width = _spell_description_bounds(column)
            for field_prefix, label in effect_fields:
                value = fields[f"{field_prefix}{card_index}"]
                if not value:
                    continue
                value = _spell_effect_value(value, label)
                effect_text = f'<font name="{SPELL_FONT_BOLD}">{label}</font> {escape(value)}'
                effect_height = _draw_wrapped_centered(
                    canvas,
                    effect_text,
                    left,
                    effect_y,
                    width,
                    SPELL_FONT,
                    7,
                    px_to_x,
                    px_to_y,
                )
                effect_y += effect_height / px_to_y + SPELL_TECHNICAL_FIELD_GAP_PX
            if fields[f"spell_tags_card_{card_index}"]:
                draw_centered(
                    fields[f"spell_tags_card_{card_index}"],
                    column,
                    base_y + SPELL_TAGS_OFFSET_Y,
                    7,
                )
            origin_text = _spell_origin_text(fields[f"spell_origin_card_{card_index}"])
            if origin_text:
                canvas.setFont(SPELL_FONT, SPELL_ORIGIN_FONT_SIZE)
                row_index = (card_index - 1) // 3
                canvas.drawString(
                    _spell_origin_x(column) * px_to_x,
                    A4[1] - (base_y + _spell_origin_offset_y(row_index)) * px_to_y,
                    origin_text,
                )
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
