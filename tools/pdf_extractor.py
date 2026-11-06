import os
import json
import pymupdf


def extract_pdf(pdf_path):
    """
    Extract text from a PDF while preserving page numbers.

    Returns a list of pages with their extracted text.
    """

    pages = []

    try:
        document = pymupdf.open(pdf_path)

        if document.is_encrypted:
            raise ValueError("PDF is encrypted.")

        for page_index, page in enumerate(document):

            text = page.get_text("text").strip()

            if text:
                pages.append({
                    "page_number": page_index + 1,
                    "text": text
                })

        document.close()

        return pages

    except Exception as error:
        print(f"[PDF Extractor] Error: {error}")
        return []


def process_pdf(pdf_path, output_dir="data/processed"):
    """Extract PDF text and save it as a JSON file."""

    os.makedirs(output_dir, exist_ok=True)

    pages = extract_pdf(pdf_path)

    filename = os.path.splitext(
        os.path.basename(pdf_path)
    )[0]

    output_path = os.path.join(
        output_dir,
        filename + ".json"
    )

    result = {
        "source_pdf": pdf_path,
        "total_pages_extracted": len(pages),
        "pages": pages
    }

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=4
        )

    print(f"[PDF Extractor] Extracted {len(pages)} pages.")
    print(f"[PDF Extractor] Saved: {output_path}")

    return result
