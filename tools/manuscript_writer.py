import os
import re
import json
import hashlib
from pathlib import Path

from langchain_core.messages import SystemMessage, HumanMessage
from config.llm import get_llm


PROMPT_VERSION = "scientific-writing-v1"


def write_scientific_sections(state, cache_path):
    """
    Generate Abstract, Introduction, and Conclusion
    using one Groq request.

    Reuse cached results when the evidence is unchanged.
    """

    # Allow tests without consuming Groq tokens.
    if os.getenv("MANUSCRIPT_AI_ENABLED", "1") == "0":
        return None

    extracted = state.get("extracted_data") or []
    synthesis = state.get("synthesis") or ""

    if not extracted or not synthesis.strip():
        raise ValueError("Scientific evidence is missing.")

    studies = []

    for index, paper in enumerate(extracted, 1):

        info = paper.get("extracted_information") or {}

        studies.append({
            "citation_id": index,
            "title": paper.get("title"),
            "year": paper.get("year"),
            "doi": paper.get("doi"),
            "methods": str(
                info.get("methods_and_approaches") or
                info.get("study_design") or ""
            )[:300],
            "findings": str(
                info.get("main_findings") or ""
            )[:450],
            "limitations": str(
                info.get("limitations") or ""
            )[:250]
        })

    evidence = {
        "topic": state.get("topic"),
        "research_question": state.get("research_question"),
        "studies": studies,
        "synthesis": synthesis
    }

    # Create a fingerprint of the evidence and model.
    fingerprint_data = {
        "version": PROMPT_VERSION,
        "model": os.getenv("GROQ_MODEL"),
        "evidence": evidence
    }

    fingerprint = hashlib.sha256(
        json.dumps(
            fingerprint_data,
            sort_keys=True,
            ensure_ascii=False,
            default=str
        ).encode("utf-8")
    ).hexdigest()

    cache_path = Path(cache_path)

    # Reuse previously generated sections.
    if cache_path.exists():

        try:
            cached = json.loads(
                cache_path.read_text(encoding="utf-8")
            )

            if cached.get("fingerprint") == fingerprint:
                print("[Manuscript] Using cached writing.")
                return cached["sections"]

        except (OSError, ValueError, KeyError):
            pass

    # One LLM invocation.
    llm = get_llm(
        max_tokens=1500,
        reasoning_effort="low"
    )

    system_prompt = """
You are an academic systematic review writer.

Write three sections using ONLY the supplied evidence.

Return valid JSON with exactly these keys:
{
  "abstract": "...",
  "introduction": "...",
  "conclusion": "..."
}

Requirements:

ABSTRACT:
- Approximately 100-130 words.
- State the research problem and objective.
- Briefly explain the review methodology.
- Summarize the main evidence-based findings.
- Do not invent numerical results.

INTRODUCTION:
- Approximately 130-170 words.
- Explain the research context and problem.
- Identify the research gap supported by the evidence.
- Explain the objective of the review.
- Support study-specific claims using citation IDs [1], [2], etc.

CONCLUSION:
- Approximately 70-100 words.
- Answer the research question using the evidence.
- Summarize important findings and implications.
- Acknowledge important limitations.

SCIENTIFIC RULES:
- Use only studies supplied in the input.
- Use only valid citation IDs.
- Never invent citations, statistics, or findings.
- Distinguish associations from causal effects.
- Do not claim causal identification without evidence.
- Do not introduce unsupported generalizations.
- Do not invent missing methodological details.
- Do not include headings inside the JSON values.
- Write in formal academic English.
- Return JSON only.
"""

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=json.dumps(
                evidence,
                ensure_ascii=False,
                default=str
            )
        )
    ])

    content = response.content

    if isinstance(content, list):
        content = "\n".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict)
        )

    # Remove optional Markdown JSON fences.
    content = str(content).strip()

    if content.startswith("```"):
        content = re.sub(
            r"^```(?:json)?\s*|\s*```$",
            "",
            content,
            flags=re.IGNORECASE
        ).strip()

    sections = json.loads(content)

    required = ["abstract", "introduction", "conclusion"]

    for key in required:

        if not isinstance(sections.get(key), str):
            raise ValueError(
                f"Invalid manuscript section: {key}"
            )

        if len(sections[key].split()) < 30:
            raise ValueError(
                f"Manuscript section too short: {key}"
            )

    # Reject citations outside the included study list.
    for key in required:

        citations = re.findall(
            r"\[(\d+)\]",
            sections[key]
        )

        for citation in citations:

            if not 1 <= int(citation) <= len(studies):
                raise ValueError(
                    f"Invalid citation [{citation}] in {key}"
                )

    # Save only successfully generated content.
    cache_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    cache_path.write_text(
        json.dumps(
            {
                "fingerprint": fingerprint,
                "sections": sections
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("[Manuscript] Scientific sections generated.")

    return sections