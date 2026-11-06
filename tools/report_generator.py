
import os
from datetime import datetime


def generate_review_report(
    state,
    output_path="outputs/systematic_review_report.md"
):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    topic = state.get("topic", "Not specified")
    protocol = state.get("protocol", {})
    prisma = state.get("prisma_data", {})
    extracted = state.get("extracted_data", [])
    quality = state.get("quality_results", [])

    lines = []

    def section(title, content):
        lines.append(f"\n## {title}\n")
        lines.append(content if content else "Not available.")

    def format_list(items):
        return "\n".join(f"- {item}" for item in items) if items else "Not available."

    # Title and status
    lines.append(f"# Systematic Literature Review: {topic}")
    lines.append(
        "\n**Generated:** " + datetime.now().strftime("%Y-%m-%d %H:%M")
    )

    validation_status = state.get("validation_status", "Not recorded")
    human_approval = state.get("human_approval", False)

    lines.append(
        f"\n**Human screening approval:** {human_approval}"
    )
    lines.append(
        f"\n**Critic validation status:** {validation_status}"
    )

    if validation_status != "APPROVED":
        lines.append(
            "\n> **Review status:** This report requires further validation. "
            "The automated critic did not approve the current synthesis."
        )
    else:
        lines.append(
            "\n> **Review status:** The automated critic approved the current "
            "synthesis. Human verification of the results and conclusions "
            "is still required."
        )

    # 1. Research question
    section(
        "1. Research Question",
        state.get("research_question", "")
    )

    # 2. Protocol
    protocol_content = [
        "### Objectives",
        format_list(protocol.get("objectives", [])),
        "\n### Inclusion Criteria",
        format_list(protocol.get("inclusion_criteria", [])),
        "\n### Exclusion Criteria",
        format_list(protocol.get("exclusion_criteria", [])),
        "\n### Keywords",
        ", ".join(protocol.get("keywords", [])) or "Not available.",
        "\n### Planned Databases",
        ", ".join(protocol.get("databases", [])) or "Not available.",
        "\n### Publication Year Range",
        str(protocol.get("publication_year_range", "Not specified")),
        "\n### Topic-Specific Extraction Dimensions",
        format_list(protocol.get("extraction_dimensions", []))
    ]

    section("2. Review Protocol", "\n".join(protocol_content))

    # 3. Search strategy
    search_queries = state.get("search_queries", [])
    retrieved_papers = state.get("retrieved_papers", [])

    search_sources = sorted({
        paper.get("source", "Not specified")
        for paper in retrieved_papers
    })

    search_content = [
        "### Search Sources",
        format_list(search_sources),
        "\n### Search Queries",
        format_list(search_queries)
    ]

    section("3. Literature Search Strategy", "\n".join(search_content))

    # 4. PRISMA statistics
    prisma_content = "\n".join(
        f"- **{key.replace('_', ' ').capitalize()}:** "
        f"{value if value is not None else 'Not available'}"
        for key, value in prisma.items()
    )

    section("4. PRISMA Statistics", prisma_content)

    diagram_path = state.get("prisma_diagram_path")

    if diagram_path:
        lines.append(
            f"\n**PRISMA flow diagram:** `{diagram_path}`"
        )

    # 5. Title and abstract screening
    screening_summary = [
        f"- Records screened: {len(state.get('screening_results', []))}",
        f"- Potentially included: {len(state.get('included_papers', []))}",
        f"- Excluded: {len(state.get('excluded_papers', []))}",
        f"- Uncertain: {len(state.get('uncertain_papers', []))}",
        f"- Human approval: {human_approval}"
    ]

    section("5. Title and Abstract Screening", "\n".join(screening_summary))

    # 6. Full-text retrieval
    retrieval_results = state.get("pdf_retrieval_results", [])

    retrieval_lines = []

    for paper in retrieval_results:
        retrieval_lines.append(
            f"- **{paper.get('title', 'Untitled')}**: "
            f"{paper.get('pdf_download_status', 'Not recorded')}"
        )

        if paper.get("pdf_error"):
            retrieval_lines.append(
                f"  - Retrieval detail: {paper['pdf_error']}"
            )

        if paper.get("pdf_text_error"):
            retrieval_lines.append(
                f"  - Text extraction detail: {paper['pdf_text_error']}"
            )

    section("6. Full-Text Retrieval", "\n".join(retrieval_lines))

    # 7. Full-text eligibility
    eligibility_results = state.get(
        "full_text_assessment_results", []
    )

    eligibility_lines = []

    for paper in eligibility_results:
        eligibility_lines.append(
            f"### {paper.get('title', 'Untitled')}\n"
            f"- **Decision:** {paper.get('decision', 'Uncertain')}\n"
            f"- **Reason:** {paper.get('reason', 'Not provided')}\n"
            f"- **Evidence pages:** "
            f"{', '.join(map(str, paper.get('evidence_pages', []))) or 'Not available'}"
        )

    section(
        "7. Full-Text Eligibility Assessment",
        "\n\n".join(eligibility_lines)
    )

    # 8. Information extraction
    extraction_sections = []

    for paper in extracted:
        info = paper.get("extracted_information", {})

        extraction_content = [
            f"### {paper.get('title', 'Untitled')}",
            f"- **Year:** {paper.get('year', 'Not reported')}",
            f"- **Extraction source:** {paper.get('extraction_source', 'Not specified')}",
            f"- **Evidence entries:** {paper.get('evidence_count', 0)}"
        ]

        universal_fields = {
            "study_type",
            "research_objective",
            "research_context",
            "participants_and_sample",
            "study_design",
            "methods_and_approaches",
            "data_sources",
            "evaluation_methods",
            "main_findings",
            "limitations",
            "missing_information"
        }

        for key in universal_fields:
            value = info.get(key, "Not reported in available text")
            extraction_content.append(
                f"- **{key.replace('_', ' ').capitalize()}:** {value}"
            )

        topic_extractions = info.get("topic_specific_extractions", {})

        if topic_extractions:
            extraction_content.append(
                "\n**Topic-specific extractions:**"
            )

            for dimension, value in topic_extractions.items():
                extraction_content.append(
                    f"- **{dimension}:** {value}"
                )

        evidence = info.get("evidence", [])

        if evidence:
            extraction_content.append("\n**Evidence traceability:**")

            for item in evidence:
                extraction_content.append(
                    f"- **{item.get('field', 'Field')}** — "
                    f"{item.get('claim', 'Claim not specified')} "
                    f"(Source: `{item.get('source_pdf', 'Unknown')}`, "
                    f"page {item.get('page_number', 'Unknown')})"
                )

        extraction_sections.append("\n".join(extraction_content))

    section(
        "8. Information Extraction",
        "\n\n".join(extraction_sections)
    )

    # 9. Quality appraisal
    appraisal_sections = []

    for paper in quality:
        appraisal = paper.get("quality_appraisal", {})
        assessments = appraisal.get("assessments", {})

        content = [
            f"### {paper.get('title', 'Untitled')}",
            f"**Study type:** {appraisal.get('study_type', 'Not established')}"
        ]

        for dimension, assessment in assessments.items():
            rating = assessment.get("rating", "Not available")
            reason = assessment.get(
                "reason", "No justification provided."
            )

            content.append(
                f"- **{dimension.replace('_', ' ').title()}:** {rating}\n"
                f"  - {reason}"
            )

        appraisal_sections.append("\n".join(content))

    section(
        "9. Quality Appraisal",
        "\n\n".join(appraisal_sections)
    )

    # 10. Synthesis
    section(
        "10. Evidence Synthesis",
        state.get("synthesis", "")
    )

    # 11. Critic evaluation
    section(
        "11. Critic Evaluation",
        state.get("critic_feedback", "")
    )

    # 12. Limitations
    limitations = [
        "Academic search coverage is limited to the sources actually implemented in the search pipeline.",
        "The protocol's planned databases should not be interpreted as searched databases unless they were actually queried.",
        "Full-text eligibility decisions are based on passages retrieved through RAG and may not represent every relevant section of a paper.",
        "Papers without accessible PDFs could not undergo full-text eligibility assessment.",
        "LLM-assisted screening, extraction, appraisal, and synthesis require human verification.",
        "The quality appraisal uses general assessment dimensions and does not yet integrate validated study-type-specific appraisal instruments.",
        "Uncertain records and reports require further human review.",
        "The generated report and PRISMA diagram should be checked against the underlying records before publication."
    ]

    section("12. Limitations", format_list(limitations))

    # 13. Execution log
    section(
        "13. Execution Log",
        format_list(state.get("execution_logs", []))
    )

    report = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(report)

    print(f"\n[Report Generator] Report saved to: {output_path}")

    return output_path