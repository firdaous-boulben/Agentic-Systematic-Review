
import os
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


def generate_prisma_diagram(
    prisma_data,
    output_path="outputs/prisma_flow.png"
):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    fig, ax = plt.subplots(figsize=(16, 14))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 16)
    ax.axis("off")

    def add_box(x, y, width, height, text):
        box = FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.12",
            edgecolor="black",
            facecolor="white",
            linewidth=1.2
        )
        ax.add_patch(box)

        ax.text(
            x + width / 2,
            y + height / 2,
            text,
            ha="center",
            va="center",
            fontsize=8,
            wrap=True
        )

    def add_arrow(start, end):
        ax.annotate(
            "",
            xy=end,
            xytext=start,
            arrowprops=dict(arrowstyle="->", linewidth=1.1)
        )

    def count_text(value):
        return "Not available" if value is None else str(value)

    # --------------------------------------------------
    # TITLE
    # --------------------------------------------------

    ax.text(
        8, 15.5,
        "PRISMA Flow Diagram",
        ha="center",
        fontsize=15,
        fontweight="bold"
    )

    # --------------------------------------------------
    # READ STATISTICS
    # --------------------------------------------------

    identified = prisma_data.get("records_identified", 0)
    duplicates = prisma_data.get("duplicates_removed", 0)
    remaining = prisma_data.get("records_after_duplicates_removed", 0)

    identified_by_source = (
        prisma_data.get("records_identified_by_source") or {}
    )

    source_lines = [
        f"{source} (n = {count})"
        for source, count in identified_by_source.items()
    ]

    source_text = "\n".join(source_lines) or "Sources not available"

    screened = prisma_data.get("records_screened", 0)
    not_screened = prisma_data.get("records_not_yet_screened", 0)
    excluded = prisma_data.get("records_excluded", 0)
    uncertain = prisma_data.get("records_uncertain", 0)
    technical_failures = prisma_data.get(
        "records_with_technical_failures", 0
    )
    not_assessed = prisma_data.get("records_not_assessed", 0)

    sought = prisma_data.get("reports_sought_for_retrieval")
    retrieved = prisma_data.get("reports_retrieved")
    not_retrieved = prisma_data.get("reports_not_retrieved")
    text_processed = prisma_data.get("reports_text_processed")
    text_processing_failed = prisma_data.get(
        "reports_text_processing_failed"
    )

    assessed = prisma_data.get("reports_assessed_for_eligibility")
    full_text_excluded = prisma_data.get("reports_excluded")
    full_text_uncertain = prisma_data.get(
        "reports_uncertain_after_full_text"
    )
    retrieval_failed = prisma_data.get(
        "reports_with_retrieval_failures"
    )
    assessment_errors = prisma_data.get(
        "reports_with_assessment_errors"
    )
    pending = prisma_data.get("reports_pending_assessment")
    final_included = prisma_data.get("studies_included")

    # --------------------------------------------------
    # IDENTIFICATION
    # --------------------------------------------------

    ax.text(
        0.5, 14.5,
        "IDENTIFICATION",
        fontsize=10,
        fontweight="bold"
    )

    add_box(
        3.5, 13.3, 5.0, 1.0,
        (
            "Records identified through academic sources\n"
            f"{source_text}\n"
            f"Total identified (n = {identified})"
        )
    )

    add_box(
        9.5, 13.3, 4.0, 1.0,
        f"Duplicate records removed\n(n = {duplicates})"
    )

    add_arrow((8.5, 13.8), (9.5, 13.8))

    add_box(
        3.5, 12.0, 5.0, 0.8,
        f"Records remaining after deduplication\n(n = {remaining})"
    )

    add_arrow((6.0, 13.3), (6.0, 12.8))

    # --------------------------------------------------
    # SCREENING
    # --------------------------------------------------

    ax.text(
        0.5, 11.2,
        "SCREENING",
        fontsize=10,
        fontweight="bold"
    )

    add_box(
        3.5, 10.2, 5.0, 0.8,
        (
            f"Records screened (n = {screened})\n"
            f"Records not screened (n = {not_screened})"
        )
    )

    add_arrow((6.0, 12.0), (6.0, 11.0))

    add_box(
        9.5, 10.2, 4.0, 0.8,
        (
            "Screening technical failures\n"
            f"(n = {technical_failures})"
        )
    )

    add_arrow((8.5, 10.6), (9.5, 10.6))

    add_box(
        0.5, 8.7, 3.5, 0.8,
        f"Records excluded\n(n = {excluded})"
    )

    add_box(
        5.0, 8.7, 3.5, 0.8,
        f"Reports sought for retrieval\n(n = {count_text(sought)})"
    )

    add_box(
        9.5, 8.7, 4.0, 0.8,
        (
            f"Records uncertain (n = {uncertain})\n"
            f"Without abstract / not assessed (n = {not_assessed})"
        )
    )

    add_arrow((4.5, 10.2), (2.25, 9.5))
    add_arrow((6.0, 10.2), (6.75, 9.5))
    add_arrow((7.5, 10.2), (11.5, 9.5))

    # --------------------------------------------------
    # RETRIEVAL
    # --------------------------------------------------

    ax.text(
        0.5, 7.7,
        "RETRIEVAL",
        fontsize=10,
        fontweight="bold"
    )

    add_box(
        2.5, 6.6, 4.0, 0.9,
        (
            f"Reports retrieved (n = {count_text(retrieved)})\n"
            f"Text processed (n = {count_text(text_processed)})"
        )
    )

    add_box(
        8.0, 6.6, 4.0, 0.9,
        (
            f"Reports not retrieved (n = {count_text(not_retrieved)})\n"
            f"Text processing failures "
            f"(n = {count_text(text_processing_failed)})"
        )
    )

    add_arrow((6.75, 8.7), (4.5, 7.5))
    add_arrow((6.75, 8.7), (10.0, 7.5))

    # --------------------------------------------------
    # ELIGIBILITY
    # --------------------------------------------------

    ax.text(
        0.5, 5.6,
        "ELIGIBILITY",
        fontsize=10,
        fontweight="bold"
    )

    add_box(
        2.5, 4.4, 4.0, 0.9,
        f"Reports assessed for eligibility\n(n = {count_text(assessed)})"
    )

    add_arrow((4.5, 6.6), (4.5, 5.3))

    add_box(
        8.0, 4.4, 4.0, 0.9,
        (
            f"Reports excluded after full-text review\n"
            f"(n = {count_text(full_text_excluded)})"
        )
    )

    add_arrow((6.5, 4.85), (8.0, 4.85))

    add_box(
        8.0, 2.9, 4.0, 1.0,
        (
            f"Full-text decisions uncertain: "
            f"{count_text(full_text_uncertain)}\n"
            f"Retrieval failures: {count_text(retrieval_failed)}\n"
            f"Assessment errors: {count_text(assessment_errors)}\n"
            f"Pending: {count_text(pending)}"
        )
    )

    add_arrow((6.0, 4.4), (8.0, 3.4))

    # --------------------------------------------------
    # FINAL INCLUSION
    # --------------------------------------------------

    ax.text(
        0.5, 2.0,
        "INCLUDED",
        fontsize=10,
        fontweight="bold"
    )

    add_box(
        3.5, 1.0, 5.0, 0.8,
        (
            "Studies included in the systematic review\n"
            f"(n = {count_text(final_included)})"
        )
    )

    add_arrow((4.5, 4.4), (6.0, 1.8))

    # --------------------------------------------------
    # EXCLUSION REASONS
    # --------------------------------------------------

    reasons = (
        prisma_data.get("full_text_exclusion_reasons") or {}
    )

    if reasons:
        reason_lines = [
            f"- {reason}: {count}"
            for reason, count in reasons.items()
        ]

        reason_text = (
            "Full-text exclusion reasons:\n"
            + "\n".join(reason_lines[:7])
        )

        if len(reason_lines) > 7:
            reason_text += (
                f"\n- Additional reasons: {len(reason_lines) - 7}"
            )

        ax.text(
            12.5, 4.8,
            reason_text,
            ha="left",
            va="top",
            fontsize=7,
            wrap=True
        )

    # --------------------------------------------------
    # SAVE
    # --------------------------------------------------

    plt.tight_layout()

    plt.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close(fig)

    print(f"[PRISMA] Diagram saved to: {output_path}")

    return output_path
