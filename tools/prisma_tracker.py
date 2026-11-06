def calculate_prisma_data(state):
    """Calculate PRISMA flow counts from the review workflow state."""

    retrieved = state.get("retrieved_papers", [])
    unique = state.get("unique_papers", [])
    screened = state.get("screening_results", [])

    excluded = state.get("excluded_papers", [])
    included_after_screening = state.get("included_papers", [])
    uncertain = state.get("uncertain_papers", [])

    # Initial screening statistics
    identified_count = len(retrieved)
    unique_count = len(unique)
    screened_count = len(screened)

    # Full-text retrieval statistics
    pdf_results = state.get("pdf_retrieval_results", [])

    reports_sought = len(included_after_screening)

    reports_retrieved = sum(
        1 for paper in pdf_results
        if paper.get("pdf_download_status") in [
            "downloaded",
            "already_available"
        ]
    )

    reports_not_retrieved = reports_sought - reports_retrieved

    # Full-text eligibility statistics
    full_text_results = state.get("full_text_assessment_results", [])

    full_text_excluded = [
        paper for paper in full_text_results
        if paper.get("decision") == "Exclude"
    ]

    full_text_included = [
        paper for paper in full_text_results
        if paper.get("decision") == "Include"
    ]

    full_text_uncertain = [
        paper for paper in full_text_results
        if paper.get("decision") == "Uncertain"
    ]

    assessed_count = len(full_text_results)

    # Group full-text exclusion reasons
    exclusion_reasons = {}

    for paper in full_text_excluded:
        reason = paper.get("reason", "Reason not specified")

        exclusion_reasons[reason] = (
            exclusion_reasons.get(reason, 0) + 1
        )

    return {
        # Identification
        "records_identified": identified_count,
        "duplicates_removed": identified_count - unique_count,
        "records_after_duplicates_removed": unique_count,

        # Title and abstract screening
        "records_screened": screened_count,
        "records_not_yet_screened": unique_count - screened_count,
        "records_excluded": len(excluded),
        "records_included_after_screening": len(included_after_screening),
        "records_uncertain": len(uncertain),

        # Full-text retrieval
        "reports_sought_for_retrieval": reports_sought,
        "reports_retrieved": reports_retrieved,
        "reports_not_retrieved": reports_not_retrieved,

        # Full-text eligibility
        "reports_assessed_for_eligibility": assessed_count,
        "reports_excluded": len(full_text_excluded),
        "full_text_exclusion_reasons": exclusion_reasons,
        "reports_uncertain_after_full_text": len(full_text_uncertain),

        # Final inclusion
        "studies_included": len(full_text_included)
    }