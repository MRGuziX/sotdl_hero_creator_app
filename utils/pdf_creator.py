import pathlib

from pypdf import PdfReader, PdfWriter


def fill_pdf(character_data: dict, output_path: str = "hero_card.pdf"):
    project_root = pathlib.Path(__file__).parent.parent
    template_path = project_root / "data_base" / "card_no_color.pdf"

    reader = PdfReader(template_path)
    writer = PdfWriter()

    writer.append(reader)

    general = character_data.get("general", {})
    backstory = character_data.get("backstory", {})
    money = character_data.get("money", [])
    equipment = character_data.get("equipment", [])

    fields = {
        "sila": str(general.get("strength", "")),
        "wola": str(general.get("will", "")),
        "intelekt": str(general.get("intelligence", "")),
        "zrecznosc": str(general.get("dexterity", "")),

        "sila_mod": str(general.get("strength", "") - 10),
        "wola_mod": str(general.get("will", "") - 10),
        "intelekt_mod": str(general.get("intelligence", "") - 10),
        "zrecznosc_mod": str(general.get("dexterity", 10) - 10),

        "percepcja": str(general.get("perception", "")),
        "obrona": str(general.get("defense", "")),
        "zdrowie": str(general.get("health", "")),
        "predkosc": str(general.get("speed", "")),
        "moc": str(general.get("power", "")),
        "obrazenia": str(general.get("damage", "")),
        "szalenstwo": str(general.get("insanity", "")),
        "splugawienie": str(general.get("corruption", "")),
        "szybkosc_zdrowienia": str(general.get("health", 0) // 4),
        "rozmiar": str(
            general.get("size", [1])[0] if isinstance(general.get("size"), list) else general.get("size", "")),

        "pochodzenie": str(general.get("ancestry_name", "")),

        "okrawki": str(money[0].get("okrawki", "")) if str(money[0].get("okrawki", "")) == "0" else "",
        "miedziaki": str(money[1].get("miedziaki", "")) if money[1].get("miedziaki", "") != "0" else "",
        "srebro": str(money[2].get("srebrniki", "")) if money[2].get("srebrniki", "") != "0" else "",
        "zloto": str(money[3].get("złote korony", "")) if money[3].get("złote korony", "") != "0" else "",

        "plecak": str(equipment[3].get("backpack", "")) if len(equipment) > 3 else "",

        "wyglad": str(backstory.get("appearance", "")) + " " + str(backstory.get("body", "")) + " " + str(
            backstory.get("age", "")),
        "osobowosc": str(backstory.get("personality", "")),
    }

    notatki_parts = []
    if backstory.get("past"):
        notatki_parts.append(str(backstory.get("past")))
    if backstory.get("religion"):
        notatki_parts.append(str(backstory.get("religion")))
        notatki_parts.append("")
    if character_data.get("professions"):
        professions = character_data.get('professions', [])
        if professions:
            notatki_parts.append(f"Profesje: {', '.join(professions)}")
        notatki_parts.append("")
    if character_data.get("oddity"):
        notatki_parts.append(f'Kuriozum: {character_data.get("oddity")}')

    fields["notatki"] = "\n".join(notatki_parts)

    # Add weapons to ekwipunek_1..5
    weapons = equipment[0].get("weapons", []) if len(equipment) > 0 else []
    for i, weapon in enumerate(weapons):
        if i < 5:
            fields[f"ekwipunek_{i + 1}"] = f"{weapon.get('name', '')} ({weapon.get('damage', '')})"

    writer.update_page_form_field_values(writer.pages[0], fields)

    output_file = pathlib.Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "wb") as output_stream:
        writer.write(output_stream)
