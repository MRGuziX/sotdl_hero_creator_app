import pathlib

from pypdf import PdfReader, PdfWriter

from models.base_hero import AncestryHero


def fill_pdf(hero: AncestryHero, output_path: str = "../output/hero_card.pdf"):
    project_root = pathlib.Path(__file__).parent.parent
    template_path = project_root / "data_base" / "card_no_color.pdf"

    reader = PdfReader(template_path)
    writer = PdfWriter()
    writer.append(reader)

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

        "okrawki": str(hero.money.okrawki) if hero.money.okrawki else "",
        "miedziaki": str(hero.money.miedziaki) if hero.money.miedziaki else "",
        "srebro": str(hero.money.srebrniki) if hero.money.srebrniki else "",
        "zloto": str(hero.money.zlote_korony) if hero.money.zlote_korony else "",

        "plecak": ", ".join(hero.equipment.backpack) if hero.equipment.backpack else "",

        "wyglad": " ".join(filter(None, [
            hero.backstory.get("appearance", ""),
            hero.backstory.get("body", ""),
            hero.backstory.get("age", ""),
            hero.backstory.get("form", ""),
        ])),
        "osobowosc": hero.backstory.get("personality", ""),
        "zamoznosc": hero.wealth.split(":")[0] if hero.wealth else "",
    }

    notatki_parts = []
    if hero.backstory.get("past"):
        notatki_parts.append(hero.backstory["past"])
        notatki_parts.append("")
    if hero.backstory.get("religion"):
        notatki_parts.append(hero.backstory["religion"])
        notatki_parts.append("")

    if hero.languages:
        lang_written = [l.name for l in hero.languages if l.can_write]
        lang_spoken = [l.name for l in hero.languages if not l.can_write]
        if lang_spoken:
            notatki_parts.append(f"Języki znane: {', '.join(lang_spoken)}")
        if lang_written:
            notatki_parts.append(f"Języki pisane: {', '.join(lang_written)}")
        notatki_parts.append("")

    if hero.professions:
        notatki_parts.append(f"Profesje: {', '.join(hero.professions)}")
        notatki_parts.append("")

    if hero.oddity:
        notatki_parts.append(f"Kuriozum: {hero.oddity}")

    fields["notatki"] = "\n".join(notatki_parts)

    for i, weapon in enumerate(hero.equipment.weapons[:5]):
        fields[f"ekwipunek_{i + 1}"] = weapon.name
        fields[f"obrazenia_{i + 1}"] = weapon.damage
        fields[f"cechy_{i + 1}"] = weapon.properties

    writer.update_page_form_field_values(writer.pages[0], fields)

    with open(output_path, "wb") as output_stream:
        writer.write(output_stream)
    return output_path
