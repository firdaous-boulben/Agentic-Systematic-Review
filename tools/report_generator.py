
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

    extraction_failures = state.get("extraction_failures", [])
    extraction_status = state.get("extraction_status", "not_recorded")

    eligible_papers = state.get("full_text_eligible_papers", [])

    lines = []

    def section(title, content):
        lines.append(f"\n## {title}\n")
        lines.append(content if content else "Not available.")

    def format_list(items):
        return (
            "\n".join(f"- {item}" for item in items)
            if items else "Not available."
        )

    def get_paper_sources(paper):
        """Return all sources associated with a paper."""
        sources = paper.get("sources") or []

        if isinstance(sources, str):
            sources = [sources]

        if not sources and paper.get("source"):
            sources = [paper["source"]]

        return sources or ["Not specified"]

    def count_records_by_source(papers):
        """Count records associated with each source."""
        counts = {}

        for paper in papers:
            for source in get_paper_sources(paper):
                counts[source] = counts.get(source, 0) + 1

        return counts

    # --------------------------------------------------
    # TITLE AND STATUS
    # --------------------------------------------------

    lines.append(f"# Systematic Literature Review: {topic}")

    lines.append(
        "\n**Generated:** "
        + datetime.now().strftime("%Y-%m-%d %H:%M")
    )

    validation_status = state.get(
        "validation_status", "Not recorded"
    )

    human_approval = state.get("human_approval", False)

    lines.append(
        f"\n**Human screening approval:** {human_approval}"
    )

    lines.append(
        f"\n**Critic validation status:** {validation_status}"
    )

    if extraction_status in ["failed", "skipped"]:
        lines.append(
            "\n> **Review status: INCOMPLETE.** "
            "Information extraction could not be completed. "
            "The results must not be interpreted as a completed systematic review."
        )

    elif extraction_status == "partially_completed":
        lines.append(
            "\n> **Review status: PARTIALLY COMPLETED.** "
            "Some eligible papers failed extraction. "
            "The findings are based only on successfully extracted papers."
        )

    elif validation_status != "APPROVED":
        lines.append(
            "\n> **Review status: REQUIRES VALIDATION.** "
            "The automated critic did not approve the current synthesis. "
            "Human verification is required."
        )

    else:
        lines.append(
            "\n> **Review status: AUTOMATED VALIDATION APPROVED.** "
            "Human verification of the results and conclusions is still required."
        )

    # --------------------------------------------------
    # 1. RESEARCH QUESTION
    # --------------------------------------------------

    section(
        "1. Research Question",
        state.get("research_question", "")
    )

    # --------------------------------------------------
    # 2. REVIEW PROTOCOL
    # --------------------------------------------------

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

    section(
        "2. Review Protocol",
        "\n".join(protocol_content)
    )

    # --------------------------------------------------
    # 3. LITERATURE SEARCH STRATEGY
    # --------------------------------------------------

    search_queries = state.get("search_queries", [])
    retrieved_papers = state.get("retrieved_papers", [])
    unique_papers = state.get("unique_papers", [])

    # Prefer counts calculated by the PRISMA tracker.
    records_by_source = prisma.get(
        "records_identified_by_source"
    )

    if records_by_source is None:
        records_by_source = count_records_by_source(
            retrieved_papers
        )

    unique_by_source = prisma.get(
        "unique_records_by_source"
    )

    if unique_by_source is None:
        unique_by_source = count_records_by_source(
            unique_papers
        )

    # Sources actually used in the search.
    search_sources = sorted(records_by_source.keys())

    if not search_sources:
        search_sources = sorted({
            source
            for paper in retrieved_papers
            for source in get_paper_sources(paper)
        })

    search_content = [
        "### Search Sources",
        format_list(search_sources),

        "\n### Records Retrieved by Source"
    ]

    if records_by_source:
        for source, count in sorted(records_by_source.items()):
            search_content.append(
                f"- **{source}:** {count} records"
            )
    else:
        search_content.append("Not available.")

    search_content.append(
        "\n### Unique Records Associated with Each Source"
    )

    if unique_by_source:
        for source, count in sorted(unique_by_source.items()):
            search_content.append(
                f"- **{source}:** {count} unique records"
            )
    else:
        search_content.append("Not available.")

    search_content.extend([
        "\n### Search Queries",
        format_list(search_queries)
    ])

    section(
        "3. Literature Search Strategy",
        "\n".join(search_content)
    )

    # --------------------------------------------------
    # 4. PRISMA STATISTICS
    # --------------------------------------------------

    prisma_content = []

    source_count_keys = {
        "records_identified_by_source",
        "unique_records_by_source"
    }

    for key, value in prisma.items():

        if key in source_count_keys:
            continue

        formatted_key = key.replace("_", " ").capitalize()

        if value is None:
            formatted_value = "Not available"

        elif isinstance(value, dict):
            formatted_value = ", ".join(
                f"{source}: {count}"
                for source, count in value.items()
            )

        else:
            formatted_value = str(value)

        prisma_content.append(
            f"- **{formatted_key}:** {formatted_value}"
        )

    section(
        "4. PRISMA Statistics",
        "\n".join(prisma_content)
    )

    diagram_path = state.get("prisma_diagram_path")

    if diagram_path:
        lines.append(
            f"\n**PRISMA flow diagram:** `{diagram_path}`"
        )

    # --------------------------------------------------
    # 5. TITLE AND ABSTRACT SCREENING
    # --------------------------------------------------

    screening_results = state.get("screening_results", [])

    completed_screening = [
        paper for paper in screening_results
        if paper.get("dual_screening_status") != "technical_error"
    ]

    technical_failures = [
        paper for paper in screening_results
        if paper.get("dual_screening_status") == "technical_error"
    ]

    included = [
        paper for paper in completed_screening
        if paper.get("screening_decision") == "Include"
    ]

    excluded = [
        paper for paper in completed_screening
        if paper.get("screening_decision") == "Exclude"
    ]

    uncertain = [
        paper for paper in completed_screening
        if paper.get("screening_decision") == "Uncertain"
    ]

    not_assessed = [
        paper for paper in screening_results
        if paper.get("dual_screening_status") == "not_assessed"
    ]

    screening_summary = [
        f"- Records received for screening: {len(screening_results)}",
        f"- Successfully screened: {len(completed_screening)}",
        f"- Potentially included: {len(included)}",
        f"- Excluded: {len(excluded)}",
        f"- Genuine uncertain decisions: {len(uncertain)}",
        f"- Not assessed (e.g. missing abstracts): {len(not_assessed)}",
        f"- Technical failures requiring retry: {len(technical_failures)}",
        f"- Human approval: {human_approval}"
    ]

    if technical_failures:
        screening_summary.append(
            "\n### Papers with Technical Screening Failures"
        )

        for paper in technical_failures:
            screening_summary.append(
                f"- **{paper.get('title', 'Untitled')}**: "
                f"{paper.get('screening_reason', 'Technical error')}"
            )

    section(
        "5. Title and Abstract Screening",
        "\n".join(screening_summary)
    )

    # --------------------------------------------------
    # 6. FULL-TEXT RETRIEVAL
    # --------------------------------------------------

    retrieval_results = state.get(
        "pdf_retrieval_results", []
    )

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

    section(
        "6. Full-Text Retrieval",
        "\n".join(retrieval_lines)
    )

    # --------------------------------------------------
    # 7. FULL-TEXT ELIGIBILITY
    # --------------------------------------------------

    eligibility_results = state.get(
        "full_text_assessment_results", []
    )

    eligibility_lines = []

    for paper in eligibility_results:
        assessment_status = paper.get(
            "assessment_status", "not_recorded"
        )

        eligibility_lines.append(
            f"### {paper.get('title', 'Untitled')}\n"
            f"- **Assessment status:** {assessment_status}\n"
            f"- **Decision:** "
            f"{paper.get('decision') or 'Not assessed'}\n"
            f"- **Reason:** {paper.get('reason', 'Not provided')}\n"
            f"- **Evidence pages:** "
            f"{', '.join(map(str, paper.get('evidence_pages', []))) or 'Not available'}"
        )

    section(
        "7. Full-Text Eligibility Assessment",
        "\n\n".join(eligibility_lines)
    )

    # --------------------------------------------------
    # 8. INFORMATION EXTRACTION
    # --------------------------------------------------

    extraction_summary = [
        f"- **Extraction status:** {extraction_status}",
        f"- **Eligible papers:** {len(eligible_papers)}",
        f"- **Successfully extracted:** {len(extracted)}",
        f"- **Failed extractions:** {len(extraction_failures)}"
    ]

    if extraction_failures:
        extraction_summary.append(
            "\n### Papers with Extraction Failures"
        )

        for failure in extraction_failures:
            extraction_summary.append(
                f"- **{failure.get('paper_title', 'Untitled')}**: "
                f"{failure.get('error', 'Unknown error')}"
            )

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
            value = info.get(
                key, "Not reported in available text"
            )

            extraction_content.append(
                f"- **{key.replace('_', ' ').capitalize()}:** {value}"
            )

        topic_extractions = info.get(
            "topic_specific_extractions", {}
        )

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
            extraction_content.append(
                "\n**Evidence traceability:**"
            )

            for item in evidence:
                extraction_content.append(
                    f"- **{item.get('field', 'Field')}** — "
                    f"{item.get('claim', 'Claim not specified')} "
                    f"(Source: `{item.get('source_pdf', 'Unknown')}`, "
                    f"page {item.get('page_number', 'Unknown')})"
                )

        extraction_sections.append(
            "\n".join(extraction_content)
        )

    section(
        "8. Information Extraction",
        "\n".join(extraction_summary)
        + "\n\n"
        + (
            "\n\n".join(extraction_sections)
            or "No papers were successfully extracted."
        )
    )

    # --------------------------------------------------
    # 9. QUALITY APPRAISAL
    # --------------------------------------------------

    appraisal_sections = []

    for paper in quality:
        appraisal = paper.get("quality_appraisal", {})
        assessments = appraisal.get("assessments", {})

        content = [
            f"### {paper.get('title', 'Untitled')}",
            f"**Study type:** {appraisal.get('study_type', 'Not established')}"
        ]

        for dimension, assessment in assessments.items():
            rating = assessment.get(
                "rating", "Not available"
            )

            reason = assessment.get(
                "reason", "No justification provided."
            )

            content.append(
                f"- **{dimension.replace('_', ' ').title()}:** {rating}\n"
                f"  - {reason}"
            )

        appraisal_sections.append(
            "\n".join(content)
        )

    section(
        "9. Quality Appraisal",
        "\n\n".join(appraisal_sections)
    )

    # --------------------------------------------------
    # 10. EVIDENCE SYNTHESIS
    # --------------------------------------------------

    section(
        "10. Evidence Synthesis",
        state.get("synthesis", "")
    )

    # --------------------------------------------------
    # 11. CRITIC EVALUATION
    # --------------------------------------------------

    section(
        "11. Critic Evaluation",
        state.get("critic_feedback", "")
    )

    # --------------------------------------------------
    # 12. LIMITATIONS
    # --------------------------------------------------

    limitations = [
        "Academic search coverage is limited to the sources actually implemented in the search pipeline.",
        "The protocol's planned databases should not be interpreted as searched databases unless they were actually queried.",
        "Records retrieved from multiple sources may overlap. Cross-source duplicates are merged during deduplication.",
        "Full-text eligibility decisions are based on passages retrieved through RAG and may not represent every relevant section of a paper.",
        "Papers without accessible PDFs could not undergo full-text eligibility assessment.",
        "LLM-assisted screening, extraction, appraisal, and synthesis require human verification.",
        "The quality appraisal uses general assessment dimensions and does not yet integrate validated study-type-specific appraisal instruments.",
        "Genuine uncertain records require human review, while technical screening failures must be retried before finalizing the review.",
        "The generated report and PRISMA diagram should be checked against the underlying records before publication."
    ]

    section(
        "12. Limitations",
        format_list(limitations)
    )

    # --------------------------------------------------
    # 13. EXECUTION LOG
    # --------------------------------------------------

    execution_logs = state.get("execution_logs", [])

    formatted_logs = [
        (
            f"[{log['timestamp']}] {log['message']}"
            if isinstance(log, dict)
            else log
        )
        for log in execution_logs
    ]

    section(
        "13. Execution Log",
        format_list(formatted_logs)
    )

    # --------------------------------------------------
    # SAVE REPORT
    # --------------------------------------------------

    report = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(report)

    print(
        f"\n[Report Generator] Report saved to: {output_path}"
    )

    return output_path
