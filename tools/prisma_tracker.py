
def get_paper_sources(paper):
    """Get normalized source names from a paper record."""

    sources = paper.get("sources") or []

    if isinstance(sources, str):
        sources = [sources]

    if not sources and paper.get("source"):
        sources = [paper["source"]]

    return {
        str(source)
        for source in sources
        if source
    } or {"Unknown"}


def count_records_by_source(papers):
    """Count records associated with each academic source."""

    counts = {}

    for paper in papers:
        for source in get_paper_sources(paper):
            counts[source] = counts.get(source, 0) + 1

    return counts


def calculate_prisma_data(state):
    """Calculate PRISMA flow counts from the review workflow state."""

    retrieved = state.get("retrieved_papers", [])
    unique = state.get("unique_papers", [])
    screened = state.get("screening_results", [])

    # --------------------------------------------------
    # IDENTIFICATION
    # --------------------------------------------------

    identified_by_source = count_records_by_source(retrieved)
    unique_by_source = count_records_by_source(unique)

    identified_count = len(retrieved)
    unique_count = len(unique)

    duplicates_removed = max(0, identified_count - unique_count)

    # --------------------------------------------------
    # TITLE AND ABSTRACT SCREENING
    # --------------------------------------------------

    technical_failures = [
        paper for paper in screened
        if paper.get("dual_screening_status") == "technical_error"
    ]

    # A record with a completed decision, an unresolved
    # disagreement, a missing abstract, or a deterministic
    # exclusion has reached the screening stage.
    completed_screening = [
        paper for paper in screened
        if paper.get("dual_screening_status") != "technical_error"
    ]

    excluded = [
        paper for paper in completed_screening
        if paper.get("screening_decision") == "Exclude"
    ]

    included_after_screening = [
        paper for paper in completed_screening
        if paper.get("screening_decision") == "Include"
    ]

    uncertain = [
        paper for paper in completed_screening
        if paper.get("screening_decision") == "Uncertain"
    ]

    not_assessed = [
        paper for paper in completed_screening
        if paper.get("dual_screening_status") == "not_assessed"
    ]

    screened_count = len(completed_screening)

    # Includes technical failures and records not processed
    # because of a screening limit.
    not_screened_count = max(0, unique_count - screened_count)

    # --------------------------------------------------
    # FULL-TEXT RETRIEVAL
    # --------------------------------------------------

    pdf_results = state.get("pdf_retrieval_results", [])

    # Human-reviewed screening inclusions are the reports
    # selected for full-text retrieval.
    reports_sought = len(state.get("included_papers", []))

    # A PDF is retrieved when a path is available.
    reports_retrieved = sum(
        1 for paper in pdf_results
        if paper.get("pdf_path")
    )

    reports_not_retrieved = max(
        0, reports_sought - reports_retrieved
    )

    # Successfully downloaded PDFs that also passed text processing.
    reports_text_processed = sum(
        1 for paper in pdf_results
        if paper.get("pdf_path")
        and paper.get("pdf_text_processed") is True
    )

    reports_text_processing_failed = sum(
        1 for paper in pdf_results
        if paper.get("pdf_path")
        and paper.get("pdf_text_processed") is False
    )

    # --------------------------------------------------
    # FULL-TEXT ELIGIBILITY
    # --------------------------------------------------

    full_text_results = state.get(
        "full_text_assessment_results", []
    )

    # Only completed assessments contribute to eligibility
    # decisions. Never count retrieval failures or errors here.
    completed_assessments = [
        paper for paper in full_text_results
        if paper.get("assessment_status") == "completed"
    ]

    full_text_excluded = [
        paper for paper in completed_assessments
        if paper.get("decision") == "Exclude"
    ]

    full_text_included = [
        paper for paper in completed_assessments
        if paper.get("decision") == "Include"
    ]

    full_text_uncertain = [
        paper for paper in completed_assessments
        if paper.get("decision") == "Uncertain"
    ]

    retrieval_failed = [
        paper for paper in full_text_results
        if paper.get("assessment_status") == "retrieval_failed"
    ]

    assessment_errors = [
        paper for paper in full_text_results
        if paper.get("assessment_status") == "error"
    ]

    pending_assessments = [
        paper for paper in full_text_results
        if paper.get("assessment_status") == "not_assessed"
    ]

    # --------------------------------------------------
    # FULL-TEXT EXCLUSION REASONS
    # --------------------------------------------------

    exclusion_reasons = {}

    for paper in full_text_excluded:
        reason = paper.get("reason") or "Reason not specified"

        exclusion_reasons[reason] = (
            exclusion_reasons.get(reason, 0) + 1
        )

    # --------------------------------------------------
    # RESULT
    # --------------------------------------------------

    return {
        # Identification
        "records_identified": identified_count,
        "records_identified_by_source": identified_by_source,
        "unique_records_by_source": unique_by_source,
        "duplicates_removed": duplicates_removed,
        "records_after_duplicates_removed": unique_count,

        # Screening
        "records_screened": screened_count,
        "records_not_yet_screened": not_screened_count,
        "records_excluded": len(excluded),
        "records_included_after_screening": len(included_after_screening),
        "records_uncertain": len(uncertain),
        "records_not_assessed": len(not_assessed),
        "records_with_technical_failures": len(technical_failures),

        # Retrieval
        "reports_sought_for_retrieval": reports_sought,
        "reports_retrieved": reports_retrieved,
        "reports_not_retrieved": reports_not_retrieved,
        "reports_text_processed": reports_text_processed,
        "reports_text_processing_failed": reports_text_processing_failed,

        # Eligibility
        "reports_assessed_for_eligibility": len(completed_assessments),
        "reports_excluded": len(full_text_excluded),
        "full_text_exclusion_reasons": exclusion_reasons,
        "reports_uncertain_after_full_text": len(full_text_uncertain),
        "reports_with_retrieval_failures": len(retrieval_failed),
        "reports_with_assessment_errors": len(assessment_errors),
        "reports_pending_assessment": len(pending_assessments),

        # Final inclusion
        "studies_included": len(full_text_included),
    }
