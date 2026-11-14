import os
from tools.pdf_extractor import process_pdf


PDF_DIRECTORY = "data/papers"

pdf_files = [
    os.path.join(PDF_DIRECTORY, filename)
    for filename in os.listdir(PDF_DIRECTORY)
    if filename.lower().endswith(".pdf")
]

print("========== PDF TEXT EXTRACTION ==========")

for pdf_path in pdf_files:

    print("\nProcessing:", os.path.basename(pdf_path))

    result = process_pdf(pdf_path)

    print("Pages extracted:", result["total_pages_extracted"])

    if result["pages"]:
        print("\nFirst page preview:")
        print(result["pages"][0]["text"][:500])
    else:
        print("No text extracted.")
