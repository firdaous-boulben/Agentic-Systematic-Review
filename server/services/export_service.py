
import re
from pathlib import Path
from html import escape

import markdown
from bs4 import BeautifulSoup, NavigableString, Tag

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    ListFlowable,
    ListItem,
    Preformatted,
)

from docx import Document
from docx.shared import Inches, Pt, RGBColor


EXPORT_ROOT = Path("outputs") / "reviews"


def _review_export_dir(review_id: str) -> Path:
    """Create a review-specific export directory using a safe identifier."""
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", str(review_id))

    if not safe_id:
        raise ValueError("Invalid review identifier.")

    directory = EXPORT_ROOT / safe_id / "exports"
    directory.mkdir(parents=True, exist_ok=True)

    return directory


def _read_report(review: dict) -> str:
    """Read the generated Markdown report associated with a review."""
    report_path = review.get("final_report")

    if not report_path:
        raise FileNotFoundError("No final report is available for this review.")

    path = Path(report_path)

    if not path.is_file():
        raise FileNotFoundError("The generated report file could not be found.")

    return path.read_text(encoding="utf-8")


def _markdown_to_soup(content: str):
    html = markdown.markdown(
        content,
        extensions=["tables", "fenced_code", "sane_lists"]
    )
    return BeautifulSoup(html, "html.parser")


def export_markdown(review_id: str, review: dict) -> Path:
    """Copy the existing report into the review's export directory."""
    content = _read_report(review)

    output = _review_export_dir(review_id) / "systematic_review_report.md"
    output.write_text(content, encoding="utf-8")

    return output


def _reportlab_inline(element) -> str:
    """Convert HTML inline elements into ReportLab-compatible markup."""
    if isinstance(element, NavigableString):
        return escape(str(element))

    if not isinstance(element, Tag):
        return ""

    content = "".join(_reportlab_inline(child) for child in element.children)
    tag = element.name

    if tag in ("strong", "b"):
        return f"<b>{content}</b>"
    if tag in ("em", "i"):
        return f"<i>{content}</i>"
    if tag == "u":
        return f"<u>{content}</u>"
    if tag == "code":
        return f'<font name="Courier">{content}</font>'
    if tag == "a":
        href = escape(element.get("href", ""), quote=True)
        return f'<link href="{href}" color="blue">{content}</link>'
    if tag == "br":
        return "<br/>"

    return content


def _pdf_blocks(parent, styles):
    """Convert Markdown-generated HTML blocks into ReportLab flowables."""
    flowables = []

    for element in parent.children:
        if isinstance(element, NavigableString):
            text = str(element).strip()
            if text:
                flowables.append(Paragraph(escape(text), styles["BodyText"]))
            continue

        if not isinstance(element, Tag):
            continue

        tag = element.name

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            style_name = {
                "h1": "Title",
                "h2": "Heading1",
                "h3": "Heading2",
                "h4": "Heading3",
                "h5": "Heading3",
                "h6": "Heading3",
            }[tag]
            flowables.append(
                Paragraph(_reportlab_inline(element), styles[style_name])
            )
            flowables.append(Spacer(1, 0.12 * cm))

        elif tag == "p":
            flowables.append(
                Paragraph(_reportlab_inline(element), styles["BodyText"])
            )
            flowables.append(Spacer(1, 0.12 * cm))

        elif tag in ("ul", "ol"):
            items = []
            for li in element.find_all("li", recursive=False):
                item_content = "".join(
                    _reportlab_inline(child) for child in li.children
                )
                items.append(
                    ListItem(
                        Paragraph(item_content, styles["BodyText"]),
                        leftIndent=12
                    )
                )

            if items:
                flowables.append(
                    ListFlowable(
                        items,
                        bulletType="bullet" if tag == "ul" else "1",
                        leftIndent=20,
                        bulletFontSize=8
                    )
                )
                flowables.append(Spacer(1, 0.15 * cm))

        elif tag == "blockquote":
            for child in element.find_all(["p"], recursive=False):
                flowables.append(
                    Paragraph(
                        _reportlab_inline(child),
                        styles["Quote"]
                    )
                )

        elif tag == "pre":
            code = element.get_text()
            flowables.append(
                Preformatted(code, styles["Code"])
            )
            flowables.append(Spacer(1, 0.15 * cm))

        elif tag == "table":
            rows = []

            for tr in element.find_all("tr"):
                cells = tr.find_all(["th", "td"], recursive=False)
                rows.append([
                    Paragraph(
                        _reportlab_inline(cell),
                        styles["TableCell"]
                    )
                    for cell in cells
                ])

            if rows:
                column_count = max(len(row) for row in rows)
                normalized_rows = [
                    row + [""] * (column_count - len(row))
                    for row in rows
                ]

                table = Table(
                    normalized_rows,
                    repeatRows=1,
                    hAlign="LEFT"
                )
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF5")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]))
                flowables.append(table)
                flowables.append(Spacer(1, 0.2 * cm))

        elif tag == "hr":
            flowables.append(Spacer(1, 0.2 * cm))

        else:
            flowables.extend(_pdf_blocks(element, styles))

    return flowables


def _add_pdf_footer(canvas, document):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(2 * cm, 1.2 * cm, "Systematic Literature Review")
    canvas.drawRightString(
        A4[0] - 2 * cm,
        1.2 * cm,
        f"Page {document.page}"
    )
    canvas.restoreState()



def export_pdf(review_id: str, review: dict) -> Path:
    """Generate a PDF from the existing Markdown report."""
    content = _read_report(review)
    soup = _markdown_to_soup(content)

    output = _review_export_dir(review_id) / "systematic_review_report.pdf"

    styles = getSampleStyleSheet()

    # Custom styles
    if "Quote" not in styles.byName:
        styles.add(ParagraphStyle(
            name="Quote",
            parent=styles["BodyText"],
            leftIndent=18,
            textColor=colors.HexColor("#475569"),
            spaceAfter=8
        ))

    if "Code" not in styles.byName:
        styles.add(ParagraphStyle(
            name="Code",
            fontName="Courier",
            fontSize=8,
            leading=10,
            leftIndent=8
        ))

    if "TableCell" not in styles.byName:
        styles.add(ParagraphStyle(
            name="TableCell",
            parent=styles["BodyText"],
            fontSize=8,
            leading=10
        ))

    document = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=review.get("topic", "Systematic Literature Review")
    )

    story = _pdf_blocks(soup, styles)

    document.build(
        story,
        onFirstPage=_add_pdf_footer,
        onLaterPages=_add_pdf_footer
    )

    return output



def _add_docx_inline(paragraph, element, bold=False, italic=False):
    """Preserve basic inline formatting when creating DOCX paragraphs."""
    if isinstance(element, NavigableString):
        run = paragraph.add_run(str(element))
        run.bold = bold
        run.italic = italic
        return

    if not isinstance(element, Tag):
        return

    tag = element.name
    new_bold = bold or tag in ("strong", "b")
    new_italic = italic or tag in ("em", "i")

    if tag == "br":
        paragraph.add_run().add_break()
        return

    for child in element.children:
        _add_docx_inline(paragraph, child, new_bold, new_italic)


def _add_docx_blocks(document, parent):
    for element in parent.children:
        if isinstance(element, NavigableString):
            text = str(element).strip()
            if text:
                document.add_paragraph(text)
            continue

        if not isinstance(element, Tag):
            continue

        tag = element.name

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = min(int(tag[1]), 3)
            paragraph = document.add_heading(level=level)
            for child in element.children:
                _add_docx_inline(paragraph, child)

        elif tag == "p":
            paragraph = document.add_paragraph()
            for child in element.children:
                _add_docx_inline(paragraph, child)

        elif tag in ("ul", "ol"):
            style = "List Bullet" if tag == "ul" else "List Number"

            for li in element.find_all("li", recursive=False):
                paragraph = document.add_paragraph(style=style)
                for child in li.children:
                    _add_docx_inline(paragraph, child)

        elif tag == "blockquote":
            for child in element.find_all("p", recursive=False):
                paragraph = document.add_paragraph(style="Quote")
                for item in child.children:
                    _add_docx_inline(paragraph, item)

        elif tag == "pre":
            paragraph = document.add_paragraph()
            run = paragraph.add_run(element.get_text())
            run.font.name = "Consolas"
            run.font.size = Pt(8)

        elif tag == "table":
            rows = element.find_all("tr")
            if not rows:
                continue

            column_count = max(
                len(row.find_all(["th", "td"], recursive=False))
                for row in rows
            )

            table = document.add_table(
                rows=0,
                cols=column_count
            )
            table.style = "Table Grid"

            for row_index, tr in enumerate(rows):
                cells = tr.find_all(["th", "td"], recursive=False)
                docx_cells = table.add_row().cells

                for index, cell in enumerate(cells):
                    paragraph = docx_cells[index].paragraphs[0]
                    for child in cell.children:
                        _add_docx_inline(paragraph, child)

                    if row_index == 0:
                        for run in paragraph.runs:
                            run.bold = True

        elif tag == "hr":
            document.add_paragraph("")

        else:
            _add_docx_blocks(document, element)


def export_docx(review_id: str, review: dict) -> Path:
    """Generate an editable DOCX document from the Markdown report."""
    content = _read_report(review)
    soup = _markdown_to_soup(content)

    output = _review_export_dir(review_id) / "systematic_review_report.docx"

    document = Document()
    document.styles["Normal"].font.name = "Calibri"
    document.styles["Normal"].font.size = Pt(10.5)

    section = document.sections[0]
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    section.left_margin = Inches(0.85)
    section.right_margin = Inches(0.85)

    _add_docx_blocks(document, soup)

    document.save(output)

    return output


def _bibtex_escape(value) -> str:
    """Escape special BibTeX characters without inventing metadata."""
    text = str(value or "").strip()

    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text.replace("{", r"\{").replace("}", r"\}")


def _get_authors(paper: dict) -> str:
    authors = paper.get("authors") or []

    if isinstance(authors, str):
        return authors

    names = []

    for author in authors:
        if isinstance(author, str):
            names.append(author)
        elif isinstance(author, dict):
            name = (
                author.get("name")
                or author.get("display_name")
                or author.get("author", {}).get("display_name")
            )
            if name:
                names.append(name)

    # OpenAlex records may store authors under authorships.
    if not names:
        for authorship in paper.get("authorships", []):
            author = authorship.get("author", {})
            name = author.get("display_name")
            if name:
                names.append(name)

    return " and ".join(names)


def _get_venue(paper: dict) -> str:
    venue = (
        paper.get("journal")
        or paper.get("venue")
        or paper.get("publication")
    )

    if isinstance(venue, dict):
        return (
            venue.get("name")
            or venue.get("display_name")
            or ""
        )

    if venue:
        return str(venue)

    primary_location = paper.get("primary_location") or {}
    source = primary_location.get("source") or {}

    return source.get("display_name", "")


def _citation_key(paper: dict, index: int) -> str:
    authors = _get_authors(paper)
    first_author = authors.split(" and ")[0] if authors else "study"

    surname = first_author.split()[-1]
    year = (
        paper.get("publication_year")
        or paper.get("year")
        or "nd"
    )

    title = paper.get("title", "reference")
    first_word = re.sub(r"[^a-zA-Z0-9]", "", title.split()[0]) if title else "ref"

    base = re.sub(
        r"[^a-zA-Z0-9]",
        "",
        f"{surname}{year}{first_word}"
    ).lower()

    return f"{base or 'reference'}{index}"


def build_bibtex(papers: list) -> str:
    """Build BibTeX entries for full-text-eligible studies only."""
    if not papers:
        return "% No full-text-eligible studies are available for this review.\n"

    entries = []
    seen = set()

    for index, paper in enumerate(papers, 1):
        if not isinstance(paper, dict):
            continue

        title = paper.get("title") or paper.get("paper_title")
        if not title:
            continue

        doi = paper.get("doi", "")
        if isinstance(doi, dict):
            doi = doi.get("value", "")

        doi = str(doi or "").replace("https://doi.org/", "").strip()

        authors = _get_authors(paper)
        year = paper.get("publication_year") or paper.get("year")
        venue = _get_venue(paper)
        url = paper.get("url") or paper.get("landing_page_url") or ""

        if not url and doi:
            url = f"https://doi.org/{doi}"

        key = _citation_key(paper, index)
        while key in seen:
            key += "a"
        seen.add(key)

        fields = {
            "title": title,
            "author": authors,
            "year": year,
            "journal": venue,
            "doi": doi,
            "url": url,
        }

        formatted_fields = [
            f"  {name} = {{{_bibtex_escape(value)}}}"
            for name, value in fields.items()
            if value not in (None, "")
        ]

        entries.append(
            "@article{" + key + ",\n"
            + ",\n".join(formatted_fields)
            + "\n}"
        )

    if not entries:
        return "% No eligible papers contained sufficient metadata for BibTeX.\n"

    return "\n\n".join(entries) + "\n"


def export_bibtex(review_id: str, review: dict) -> Path:
    """Export references from the final full-text-eligible paper set."""
    papers = review.get("full_text_eligible_papers", [])
    content = build_bibtex(papers)

    output = _review_export_dir(review_id) / "references.bib"
    output.write_text(content, encoding="utf-8")

    return output
