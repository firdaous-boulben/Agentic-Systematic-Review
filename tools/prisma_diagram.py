import os
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


def generate_prisma_diagram(
    prisma_data,
    output_path="outputs/prisma_flow.png"
):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    fig, ax = plt.subplots(figsize=(15, 13))
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 15)
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
            fontsize=8.5,
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

    ax.text(
        7.5, 14.5,
        "PRISMA Flow Diagram",
        ha="center",
        fontsize=15,
        fontweight="bold"
    )

    # Read PRISMA statistics
    identified = prisma_data.get("records_identified", 0)
    duplicates = prisma_data.get("duplicates_removed", 0)
    remaining = prisma_data.get("records_after_duplicates_removed", 0)

    screened = prisma_data.get("records_screened", 0)
    not_screened = prisma_data.get("records_not_yet_screened", 0)
    excluded = prisma_data.get("records_excluded", 0)
    included = prisma_data.get("records_included_after_screening", 0)
    uncertain = prisma_data.get("records_uncertain", 0)

    sought = prisma_data.get("reports_sought_for_retrieval")
    retrieved = prisma_data.get("reports_retrieved")
    not_retrieved = prisma_data.get("reports_not_retrieved")

    assessed = prisma_data.get("reports_assessed_for_eligibility")
    full_text_excluded = prisma_data.get("reports_excluded")
    full_text_uncertain = prisma_data.get(
        "reports_uncertain_after_full_text"
    )
    final_included = prisma_data.get("studies_included")

    # Identification
    ax.text(0.5, 13.4, "IDENTIFICATION", fontsize=10, fontweight="bold")

    add_box(
        3.5, 12.7, 4.5, 0.8,
        f"Records identified through academic search\n(n = {identified})"
    )

    add_box(
        9.0, 12.7, 4.0, 0.8,
        f"Duplicate records removed\n(n = {duplicates})"
    )

    add_arrow((8.0, 13.1), (9.0, 13.1))

    add_box(
        3.5, 11.4, 4.5, 0.8,
        f"Records remaining after deduplication\n(n = {remaining})"
    )
    add_arrow((5.75, 12.7), (5.75, 12.2))

    # Screening
    ax.text(0.5, 10.4, "SCREENING", fontsize=10, fontweight="bold")

    add_box(
        3.5, 9.5, 4.5, 0.8,
        f"Records screened\n(n = {screened})"
    )
    add_arrow((5.75, 11.4), (5.75, 10.3))

    add_box(
        9.0, 9.5, 4.0, 0.8,
        f"Records not screened\n(n = {not_screened})"
    )
    add_arrow((8.0, 9.9), (9.0, 9.9))

    add_box(
        0.7, 8.0, 3.3, 0.8,
        f"Records excluded\n(n = {excluded})"
    )

    add_box(
        5.0, 8.0, 3.3, 0.8,
        f"Reports sought for retrieval\n(n = {count_text(sought)})"
    )

    add_box(
        9.5, 8.0, 4.0, 0.8,
        f"Records uncertain at screening\n(n = {uncertain})"
    )

    add_arrow((4.5, 9.5), (2.35, 8.8))
    add_arrow((5.75, 9.5), (6.65, 8.8))
    add_arrow((7.5, 9.5), (11.5, 8.8))

    # Retrieval
    ax.text(0.5, 7.0, "RETRIEVAL", fontsize=10, fontweight="bold")

    add_box(
        2.5, 6.0, 4.0, 0.8,
        f"Reports retrieved\n(n = {count_text(retrieved)})"
    )

    add_box(
        8.0, 6.0, 4.0, 0.8,
        f"Reports not retrieved\n(n = {count_text(not_retrieved)})"
    )

    add_arrow((6.65, 8.0), (4.5, 6.8))
    add_arrow((6.65, 8.0), (10.0, 6.8))

    # Eligibility
    ax.text(0.5, 5.0, "ELIGIBILITY", fontsize=10, fontweight="bold")

    add_box(
        2.5, 4.0, 4.0, 0.8,
        f"Reports assessed for eligibility\n(n = {count_text(assessed)})"
    )
    add_arrow((4.5, 6.0), (4.5, 4.8))

    add_box(
        8.0, 4.0, 4.0, 0.8,
        f"Reports excluded after full-text review\n(n = {count_text(full_text_excluded)})"
    )
    add_arrow((6.5, 4.4), (8.0, 4.4))

    add_box(
        8.0, 2.8, 4.0, 0.7,
        f"Full-text decisions uncertain\n(n = {count_text(full_text_uncertain)})"
    )

    add_arrow((6.0, 4.0), (8.0, 3.15))

    # Final inclusion
    ax.text(0.5, 2.0, "INCLUDED", fontsize=10, fontweight="bold")

    add_box(
        3.5, 1.0, 5.0, 0.8,
        f"Studies included in the systematic review\n(n = {count_text(final_included)})"
    )

    add_arrow((4.5, 4.0), (6.0, 1.8))

    # Exclusion reasons
    reasons = prisma_data.get("full_text_exclusion_reasons") or {}

    if reasons:
        reason_lines = [
            f"- {reason}: {count}"
            for reason, count in reasons.items()
        ]

        reason_text = "Full-text exclusion reasons:\n" + "\n".join(
            reason_lines[:5]
        )

        if len(reason_lines) > 5:
            reason_text += f"\n- Other reasons: {len(reason_lines) - 5} more"

        ax.text(
            13.2, 3.8,
            reason_text,
            ha="left",
            va="top",
            fontsize=7.5,
            wrap=True
        )

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"[PRISMA] Diagram saved to: {output_path}")

    return output_path
