from pathlib import Path
import re
from tools.manuscript_writer import write_scientific_sections


def generate_manuscript(
    state,
    output_path="outputs/systematic_review_manuscript.md"
):
    """
    Generate an academic manuscript draft from completed
    systematic review results.

    No additional LLM calls.
    """

    topic = state.get("topic", "Systematic Literature Review")
    research_question = state.get("research_question", "")

    protocol = state.get("protocol") or {}
    prisma = state.get("prisma_data") or {}

    extracted = state.get("extracted_data") or []
    synthesis = state.get("synthesis") or ""

    if not extracted or not synthesis.strip():
        raise ValueError(
            "A completed extraction and synthesis are required "
            "to generate the scientific manuscript."
        )

    def as_list(value):
        if not value:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def format_authors(paper):
        authors = as_list(paper.get("authors"))

        names = []

        for author in authors:
            if isinstance(author, str):
                names.append(author)

            elif isinstance(author, dict):
                name = (
                    author.get("name")
                    or author.get("display_name")
                )
                if name:
                    names.append(name)

        return ", ".join(names) or "Author information unavailable"

    def clean(value):
        return str(value or "Not reported").replace("|", "\\|")

    def format_criteria(items):
        return "\n".join(
            f"- {item}" for item in as_list(items)
        ) or "Not specified."

    # Generate evidence-based scientific writing.
    scientific_sections = write_scientific_sections(
        state,
        cache_path=Path(output_path).with_suffix(
            ".sections_cache.json"
        )
    )

    sections = []

    # TITLE
    sections.append(f"# {topic}")

    # ABSTRACT
    sections.append("## Abstract")

    sections.append(
        scientific_sections["abstract"]
        if scientific_sections
        else (
            f"This systematic literature review investigates "
            f"{research_question or topic}. "
            "A structured literature search, screening, "
            "and evidence synthesis were conducted."
        )
    )

    # KEYWORDS
    keywords = as_list(protocol.get("keywords"))

    sections.append(
        "**Keywords:** " +
        (", ".join(map(str, keywords)) if keywords else topic)
    )

    # INTRODUCTION
    sections.append("## 1. Introduction")

    sections.append(
        scientific_sections["introduction"]
        if scientific_sections
        else (
            "This review addresses the research question: "
            f"{research_question or topic}."
        )
    )

    objectives = as_list(protocol.get("objectives"))

    if objectives:
        sections.append(
            "The review objectives are:\n\n" +
            format_criteria(objectives)
        )

    # METHODOLOGY
    sections.append("## 2. Methodology")

    sections.append(
        "The review employed a structured study-selection "
        "process involving identification, deduplication, "
        "title and abstract screening, full-text eligibility "
        "assessment, and information extraction."
    )

    sources = (
        prisma.get("records_identified_by_source") or {}
    )

    if sources:
        sections.append(
            "### 2.1 Information sources\n\n" +
            ", ".join(sources.keys())
        )

    queries = as_list(state.get("search_queries"))

    if queries:
        sections.append(
            "### 2.2 Search strategy\n\n" +
            format_criteria(queries)
        )

    sections.append(
        "### 2.3 Inclusion criteria\n\n" +
        format_criteria(protocol.get("inclusion_criteria"))
    )

    sections.append(
        "### 2.4 Exclusion criteria\n\n" +
        format_criteria(protocol.get("exclusion_criteria"))
    )

    # PRISMA
    sections.append("### 2.5 Study selection")

    sections.append(
        f"Records identified: "
        f"{prisma.get('records_identified', 'Not reported')}. "
        f"Duplicates removed: "
        f"{prisma.get('duplicates_removed', 'Not reported')}. "
        f"Records screened: "
        f"{prisma.get('records_screened', 'Not reported')}. "
        f"Full-text reports assessed: "
        f"{prisma.get('reports_assessed_for_eligibility', 'Not reported')}. "
        f"Studies included: "
        f"{prisma.get('studies_included', 'Not reported')}."
    )

    # RESULTS
    sections.append("## 3. Results")

    sections.append("### 3.1 Characteristics of included studies")

    table = [
        "| Study | Year | Methodology |",
        "|---|---|---|"
    ]

    for index, paper in enumerate(extracted, start=1):

        info = paper.get("extracted_information") or {}

        methods = clean(
            info.get("methods_and_approaches")
            or info.get("study_design")
        )

        # Keep the table compact.
        methods = methods[:160]

        table.append(
            f"| [{index}] {clean(paper.get('title'))} "
            f"| {clean(paper.get('year'))} "
            f"| {methods} |"
        )

    sections.append("\n".join(table))

    # SCIENTIFIC SYNTHESIS STRUCTURE
    synthesis_parts = re.split(
        r"(?m)^###\s+(.+?)\s*$",
        synthesis
    )

    sections.append("### 3.2 Comparative Findings")

    # Handle synthesis without recognized headings.
    if len(synthesis_parts) == 1:
        sections.append(synthesis.strip())

    else:
        introduction_text = synthesis_parts[0].strip()

        if introduction_text:
            sections.append(introduction_text)

        discussion = None
        limitations = None

        for i in range(1, len(synthesis_parts), 2):

            heading = synthesis_parts[i].strip()
            content = synthesis_parts[i + 1].strip()

            if not content:
                continue

            heading_lower = heading.lower()

            if heading_lower == "discussion":
                discussion = content

            elif "limitation" in heading_lower:
                limitations = content

            else:
                sections.append(f"### {heading}")
                sections.append(content)

        if discussion:
            sections.append("## 4. Discussion")
            sections.append(discussion)

        if limitations:
            sections.append("## 5. Limitations")
            sections.append(limitations)

    # CONCLUSION
    sections.append("## 6. Conclusion")

    sections.append(
        scientific_sections["conclusion"]
        if scientific_sections
        else (
            f"This review examines {research_question or topic}. "
            "The conclusions should be interpreted in relation "
            "to the quality and completeness of the evidence."
        )
    )
    # REFERENCES
    sections.append("## References")

    for index, paper in enumerate(extracted, start=1):

        authors = format_authors(paper)
        year = paper.get("year") or "n.d."
        title = paper.get("title") or "Untitled"
        doi = paper.get("doi") or ""

        reference = (
            f"[{index}] {authors} ({year}). "
            f"{title}."
        )

        if doi:
            reference += f" {doi}"

        sections.append(reference)

    manuscript = "\n\n".join(sections)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(
        manuscript,
        encoding="utf-8"
    )

    print(
        f"[Manuscript Generator] Saved: {output}"
    )

    return str(output)