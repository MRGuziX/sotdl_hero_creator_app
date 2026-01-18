from pypdf import PdfReader, PdfWriter
import pathlib

def fill_pdf(character_data: dict, output_path: str = "hero_card.pdf"):
    project_root = pathlib.Path(__file__).parent.parent
    template_path = project_root / "data_base" / "card_no_color.pdf"
    
    reader = PdfReader(template_path)
    writer = PdfWriter()

    writer.append(reader)

    # get_hero returns dict with attributes under 'general' key
    # strength, will, intelligence, dexterity
    # sila, wola, intelekt, zrecznosc
    
    general = character_data.get("general", {})
    
    fields = {
        "sila": str(general.get("strength", "")),
        "wola": str(general.get("will", "")),
        "intelekt": str(general.get("intelligence", "")),
        "zrecznosc": str(general.get("dexterity", ""))
    }

    writer.update_page_form_field_values(writer.pages[0], fields)

    with open(output_path, "wb") as output_stream:
        writer.write(output_stream)
