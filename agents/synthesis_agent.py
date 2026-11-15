
import json
import re
import time

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate

from config.llm import get_llm
from server.utils.logging import add_execution_logs

load_dotenv()

# Keep individual requests small enough for the Groq TPM limit.
study_llm = get_llm(max_tokens=600)
final_llm = get_llm(max_tokens=1800)


# ---------------------------------------------------------
# Prompts
# ---------------------------------------------------------

study_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an academic research analyst.

Analyze ONE extracted academic study for a systematic review.

Produce a concise, evidence-based analytical summary covering:
1. Research objective and context.
2. Study design and methods.
3. Topic-specific variables, methods and outcomes relevant to the research question.4. Main findings and reported outcomes.
5. Challenges and limitations.
6. Missing or insufficiently reported information.
7. Methodological quality, using only the supplied appraisal.

Use the original bibliographic metadata as authoritative.
If extracted information conflicts with that metadata,
explicitly flag the inconsistency.

Do not invent results, sample sizes, metrics, or references.
Distinguish reported findings from proposed capabilities.
Do not interpret missing information as a negative result.

Keep the summary concise (approximately 200-300 words).
Prioritize findings, methods, limitations, and evidence
references relevant to the research question.
Preserve the supplied evidence references using their
PDF filenames and page numbers."""
    ),
    (
        "human",
        """Review topic: {topic}

Research question: {research_question}

Study information:
{paper_data}

Produce the analytical study summary."""
    )
])

final_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an academic research synthesis specialist.

Produce a rigorous, critical, evidence-based synthesis
of the supplied studies in relation to the research topic,
research question, and approved protocol.

ORGANIZATION:

Write a scientific synthesis with these Markdown headings:

### Comparative Findings
Compare the main findings across the included studies.
Identify agreements, disagreements, and differences
in reported outcomes.

### Discussion
Interpret the findings in relation to the research question.
Compare methodological approaches and explain how study
quality affects the interpretation of the evidence.
Identify research gaps and implications.

### Limitations of the Evidence
Explain limitations supported by the included studies,
including methodological weaknesses, missing information,
and limitations in the available evidence.

CITATION RULES:
- Each study has a citation_id.
- Cite studies using [1], [2], etc.
- Use only citation IDs supplied in the study summaries.
- Never invent references, results, or statistics.
- Every substantive finding must be supported by a study.
- Do not write an abstract, introduction, or bibliography.
- Avoid repeating the same findings across sections.

EVIDENCE AND TRACEABILITY:

- Support claims with study titles and publication years.
- Identify the studies supporting each finding.
- Preserve supplied PDF filenames and page references
  when discussing evidence.
- Include numerical results only when explicitly reported.
- Never invent statistics, findings, or references.
- Distinguish reported results from proposed capabilities.
- Distinguish primary studies from review studies.
- Do not treat review conclusions as independent
  experimental findings.
- Flag metadata inconsistencies rather than silently
  choosing an unsupported value.

CRITICAL SYNTHESIS:

- Compare studies rather than simply listing them.
- Identify agreements, differences, and contradictions.
- Discuss methodological strengths and weaknesses
  using the supplied quality appraisal.
- Explain how study quality affects interpretation.
- Identify missing evidence and research gaps.
- Do not generalize beyond the supplied studies.
- Acknowledge preliminary, incomplete, or abstract-only
  evidence where applicable.

ACADEMIC STYLE:

Write in clear academic English, using coherent
paragraphs and meaningful transitions.
Prioritize critical comparison and synthesis.
Maintain a cautious academic tone."""
    ),
    (
        "human",
        """Research topic: {topic}

Research question: {research_question}

Approved review protocol:
{protocol_data}

Topic-specific extraction dimensions:
{extraction_dimensions}

Individual study analyses:
{study_summaries}

Produce the final comparative evidence synthesis."""
    )
])

study_chain = study_prompt | study_llm
final_chain = final_prompt | final_llm


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def compact_study(paper, appraisal):
    """Keep relevant extracted information and evidence references."""

    info = paper.get("extracted_information", {}) or {}

    relevant_fields = [
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
        "missing_information",
        "topic_specific_extractions"
    ]

    compact_info = {
        field: info[field]
        for field in relevant_fields
        if field in info
    }

    # Keep claims and page references, but omit long passages.
    evidence_refs = []

    for item in info.get("evidence", []):
        evidence_refs.append({
            "field": item.get("field"),
            "claim": item.get("claim"),
            "source_pdf": item.get("source_pdf"),
            "page_number": item.get("page_number")
        })

    return {
        "bibliographic_metadata": {
            "title": paper.get("title"),
            "authors": paper.get("authors", []),
            "year": paper.get("year"),
            "doi": paper.get("doi"),
            "url": paper.get("url"),
            "source": paper.get("source")
        },
        "extraction_source": paper.get(
            "extraction_source", "unknown"
        ),
        "extracted_information": compact_info,
        "evidence_references": evidence_refs,
        "quality_appraisal": appraisal or {}
    }


def normalize_text(value):
    return str(value or "").strip().lower()


def get_appraisal_for_paper(paper, quality_results):
    """Match appraisal using DOI, OpenAlex ID, or title."""

    paper_doi = normalize_text(paper.get("doi"))
    paper_id = normalize_text(paper.get("openalex_id"))
    paper_title = normalize_text(paper.get("title"))

    for result in quality_results:
        result_doi = normalize_text(result.get("doi"))
        result_id = normalize_text(result.get("openalex_id"))
        result_title = normalize_text(
            result.get("title") or result.get("paper_title")
        )

        if (
            (paper_doi and result_doi == paper_doi)
            or (paper_id and result_id == paper_id)
            or (paper_title and result_title == paper_title)
        ):
            return result.get(
                "quality_appraisal",
                result
            )

    return paper.get("quality_appraisal", {})


def invoke_with_retry(chain, payload, label, max_attempts=4):
    """Retry temporary rate-limit and service errors."""

    for attempt in range(max_attempts):
        try:
            return chain.invoke(payload)

        except Exception as exc:
            error_text = str(exc).lower()

            status_code = getattr(exc, "status_code", None)

            is_rate_limit = (
                status_code == 429
                or "429" in error_text
                or "rate limit" in error_text
                or "too many requests" in error_text
            )

            is_temporary = (
                is_rate_limit
                or status_code in (500, 502, 503, 504)
                or "temporarily unavailable" in error_text
                or "timeout" in error_text
            )

            if not is_temporary or attempt == max_attempts - 1:
                if status_code == 413 or "request too large" in error_text:
                    raise RuntimeError(
                        f"{label}: Request still exceeds the model's "
                        "input/token limit. Reduce the study payload."
                    ) from exc

                raise

            # Use the provider's suggested delay when available.
            match = re.search(
                r"try again in ([0-9.]+)\s*s",
                error_text
            )

            wait_seconds = (
                float(match.group(1)) + 2
                if match
                else 20 * (attempt + 1)
            )

            print(
                f"[Synthesis Agent] {label} temporarily failed. "
                f"Retrying in {wait_seconds:.1f} seconds "
                f"(attempt {attempt + 1}/{max_attempts})."
            )

            time.sleep(wait_seconds)


def response_to_text(response):
    content = response.content

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        return "\n".join(
            item.get("text", str(item))
            if isinstance(item, dict)
            else str(item)
            for item in content
        )

    return str(content)


# ---------------------------------------------------------
# Main synthesis agent
# ---------------------------------------------------------

def run_synthesis_agent(state):
    print("\n[Synthesis Agent] Starting evidence synthesis...")

    papers = state.get("extracted_data", [])
    quality_results = state.get("quality_results", [])
    protocol = state.get("protocol", {}) or {}

    if not papers:
        print("[Synthesis Agent] No extracted papers available.")

        return {
            "synthesis": "",
            "current_stage": "synthesis_skipped",
            "execution_logs": add_execution_logs(
                state.get("execution_logs", []),
                ["Synthesis skipped: no extracted papers available."]
            )
        }

    topic = state.get("topic", "Not specified")

    research_question = state.get(
        "research_question",
        protocol.get("research_question", "Not specified")
    )

    protocol_summary = {
        "research_question": protocol.get("research_question"),
        "objectives": protocol.get("objectives", []),
        "inclusion_criteria": protocol.get("inclusion_criteria", []),
        "exclusion_criteria": protocol.get("exclusion_criteria", [])
    }

    extraction_dimensions = protocol.get(
        "extraction_dimensions", []
    )

    study_summaries = []

    print(
        f"[Synthesis Agent] Processing {len(papers)} studies "
        "individually..."
    )

    # -----------------------------------------------------
    # Stage 1: Analyze each study separately
    # -----------------------------------------------------

    for index, paper in enumerate(papers):
        title = paper.get("title", f"Study {index + 1}")

        print(
            f"\n[Synthesis Agent] Study {index + 1}/{len(papers)}: "
            f"{title}"
        )

        appraisal = get_appraisal_for_paper(
            paper,
            quality_results
        )

        compact_data = compact_study(paper, appraisal)

        paper_json = json.dumps(
            compact_data,
            ensure_ascii=False
        )

        print(
            f"[Synthesis Agent] Study input: "
            f"{len(paper_json):,} characters"
        )

        response = invoke_with_retry(
            study_chain,
            {
                "topic": topic,
                "research_question": research_question,
                "paper_data": json.dumps(
                    compact_data,
                    indent=2,
                    ensure_ascii=False
                )
            },
            f"Study {index + 1}"
        )

        study_summary = response_to_text(response)

        study_summaries.append({
            "citation_id": index + 1,
            "title": paper.get("title"),
            "authors": paper.get("authors", []),
            "year": paper.get("year"),
            "doi": paper.get("doi"),
            "analysis": study_summary
        })

        print(
            f"[Synthesis Agent] Study {index + 1} analysis completed."
        )

        # Space requests to reduce TPM pressure.
        if index < len(papers) - 1:
            time.sleep(18)

    # -----------------------------------------------------
    # Stage 2: Comparative synthesis
    # -----------------------------------------------------

    print(
        "\n[Synthesis Agent] Preparing comparative synthesis..."
    )

    summaries_json = json.dumps(
        study_summaries,
        indent=2,
        ensure_ascii=False
    )

    print(
        f"[Synthesis Agent] Study summaries: "
        f"{len(summaries_json):,} characters"
    )

    # Allow the individual requests' token usage to replenish.
    time.sleep(20)

    print("[Synthesis Agent] Sending final synthesis request...")

    response = invoke_with_retry(
        final_chain,
        {
            "topic": topic,
            "research_question": research_question,
            "protocol_data": json.dumps(
                protocol_summary,
                indent=2,
                ensure_ascii=False
            ),
            "extraction_dimensions": json.dumps(
                extraction_dimensions,
                indent=2,
                ensure_ascii=False
            ),
            "study_summaries": summaries_json
        },
        "Final synthesis"
    )

    synthesis = response_to_text(response)

    if not synthesis.strip():
        raise RuntimeError(
            "The synthesis model returned an empty response."
        )

    print("[Synthesis Agent] Evidence synthesis completed.")

    return {
        "synthesis": synthesis,
        "current_stage": "synthesis_completed",
        "execution_logs": add_execution_logs(
            state.get("execution_logs", []),
            [
                f"Individual analyses generated for {len(papers)} studies.",
                f"Comparative synthesis generated using {len(papers)} studies."
            ]
        )
    }
