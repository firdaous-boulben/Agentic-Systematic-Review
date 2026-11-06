
import os
import re
import requests
from urllib.parse import urlparse


DEFAULT_OUTPUT_DIR = "data/papers"


def create_filename(title):
    """Create a safe filename from a paper title."""

    filename = re.sub(r'[<>:"/\\|?*]', "", title or "untitled")
    filename = re.sub(r"\s+", "_", filename.strip())

    return filename[:120] + ".pdf"


def is_valid_pdf(filepath):
    """Check whether a file has a valid PDF signature."""

    if not os.path.isfile(filepath):
        return False

    try:
        with open(filepath, "rb") as file:
            return b"%PDF-" in file.read(1024)
    except OSError:
        return False


def download_pdf(paper, output_dir=DEFAULT_OUTPUT_DIR):

    os.makedirs(output_dir, exist_ok=True)

    title = paper.get("title") or "Untitled"
    filename = create_filename(title)

    filepath = os.path.join(output_dir, filename)
    temporary_path = filepath + ".part"

    paper["pdf_path"] = None
    paper["pdf_download_status"] = "not_attempted"
    paper["pdf_error"] = None

    # Reuse an existing valid PDF.
    if is_valid_pdf(filepath):

        paper["pdf_path"] = filepath
        paper["pdf_download_status"] = "already_available"

        print(f"[PDF] Reusing existing PDF: {filename}")

        return paper

    pdf_url = paper.get("pdf_url")

    if not pdf_url:

        paper["pdf_download_status"] = "unavailable"
        paper["pdf_error"] = "No direct PDF URL available."

        print(f"[PDF] No direct PDF URL: {title}")

        return paper

    if urlparse(pdf_url).scheme not in ("http", "https"):

        paper["pdf_download_status"] = "failed"
        paper["pdf_error"] = "Invalid PDF URL."

        return paper

    try:

        print(f"\n[PDF] Downloading: {title}")

        response = requests.get(
            pdf_url,
            headers={
                "User-Agent": "AcademicSystematicReview/1.0"
            },
            timeout=(15, 60),
            stream=True
        )

        response.raise_for_status()

        with open(temporary_path, "wb") as file:

            for chunk in response.iter_content(chunk_size=8192):

                if chunk:
                    file.write(chunk)

        if not is_valid_pdf(temporary_path):

            raise ValueError(
                "The downloaded content is not a valid PDF."
            )

        os.replace(temporary_path, filepath)

        paper["pdf_path"] = filepath
        paper["pdf_download_status"] = "downloaded"

        print(f"[PDF] Successfully saved: {filepath}")

    except Exception as error:

        paper["pdf_download_status"] = "failed"
        paper["pdf_error"] = str(error)

        print(f"[PDF] Download failed: {error}")

    finally:

        if os.path.exists(temporary_path):
            os.remove(temporary_path)

    return paper


def retrieve_pdfs(papers, output_dir=DEFAULT_OUTPUT_DIR):

    updated_papers = []

    for paper in papers:

        updated_paper = download_pdf(
            paper,
            output_dir
        )

        updated_papers.append(updated_paper)

    downloaded = sum(
        p["pdf_download_status"] == "downloaded"
        for p in updated_papers
    )

    already_available = sum(
        p["pdf_download_status"] == "already_available"
        for p in updated_papers
    )

    unavailable = sum(
        p["pdf_download_status"] == "unavailable"
        for p in updated_papers
    )

    failed = sum(
        p["pdf_download_status"] == "failed"
        for p in updated_papers
    )

    print("\n========== PDF RETRIEVAL SUMMARY ==========")
    print("Total papers:", len(updated_papers))
    print("Newly downloaded:", downloaded)
    print("Already available:", already_available)
    print("No PDF URL available:", unavailable)
    print("Download failed:", failed)

    return updated_papers