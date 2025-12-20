from pypdf import PdfReader, PdfWriter
import io


def fill_pdf_form(hero_data: dict, template_path: str) -> io.BytesIO:
    """
    Fills an editable PDF form with hero data.
    :param hero_data: The dictionary returned by build_hero
    :param template_path: Path to your editable PDF template
    :return: BytesIO object containing the filled PDF
    """
    reader = PdfReader(template_path)
    writer = PdfWriter()

    # Copy pages from reader to writer
    page = reader.pages[0]
    writer.add_page(page)

    # Flatten the hero_data for the PDF fields
    # This maps JSON keys to PDF field names
    fields = {
        "ancestry": hero_data["general"].get("ancestry", ""),
        "strength": str(hero_data["general"].get("strength", "")),
        "dexterity": str(hero_data["general"].get("dexterity", "")),
        "intelligence": str(hero_data["general"].get("intelligence", "")),
        "will": str(hero_data["general"].get("will", "")),
        # You can join backstory descriptions into one field
        "backstory": "\n".join([f"{k}: {v}" for k, v in hero_data.get("backstory", {}).items()])
    }

    # Fill the form fields
    writer.update_page_form_field_values(writer.pages[0], fields)

    # Write to a bytes buffer
    output_stream = io.BytesIO()
    writer.write(output_stream)
    output_stream.seek(0)

    return output_stream