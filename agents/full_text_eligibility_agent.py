
import json
import time
import os
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from config.llm import get_llm
from rag.retriever import PaperRetriever
from server.utils.logging import add_execution_logs


llm = get_llm()
parser = JsonOutputParser()


# ELIGIBILITY ASSESSMENT PROMPT

eligibility_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an academic full-text eligibility assessor
conducting a systematic literature review.

Your task is to evaluate the supplied research paper against
the approved inclusion and exclusion criteria.

ASSESSMENT PROCEDURE:

1. Evaluate EVERY inclusion criterion separately.
2. Evaluate EVERY exclusion criterion separately.
3. For each criterion, assign one of these statuses:
   - Met: Explicit full-text evidence supports the criterion.
   - Not met: Explicit full-text evidence demonstrates that
     the criterion is not satisfied.
   - Unclear: The available evidence is insufficient to
     determine whether the criterion is satisfied.
4. Provide specific supporting evidence for each assessment.
5. Identify the page number where the evidence appears.

DECISION RULES:

1. Include:
   All mandatory inclusion criteria are met, and no exclusion
   criterion is met.

2. Exclude:
   At least one mandatory inclusion criterion is explicitly
   not met, or at least one exclusion criterion is explicitly
   met.

3. Uncertain:
   The available evidence does not allow a reliable decision,
   and neither inclusion nor exclusion can be established.

IMPORTANT RULES:

- Base every assessment exclusively on the supplied evidence.
- Do not assume a criterion is satisfied because no
  contradictory evidence was retrieved.
- Do not interpret missing information as evidence that
  a criterion is not met.
- Distinguish clearly between "Not reported" and "Not met".
- Do not invent evidence, page numbers, or study characteristics.
- If evidence for a criterion is unavailable, mark it Unclear.
- Evaluate inclusion and exclusion criteria independently.
- Do not use information from other papers.
- Do not treat the abstract alone as sufficient full-text
  evidence.
- Preserve the original wording of each eligibility criterion.
- Ensure the overall decision is consistent with the
  individual criterion assessments.

OUTPUT REQUIREMENTS:

Return valid JSON only, without Markdown formatting or
additional commentary.

Return exactly these four top-level keys:

{{
    "decision": "Include, Exclude, or Uncertain",
    "reason": "Explanation of the eligibility decision.",
    "criterion_assessments": [
        {{
            "criterion": "The exact eligibility criterion",
            "status": "Met | Not met | Unclear",
            "evidence": "Relevant evidence from the full text",
            "page": 5
        }}
    ],
    "evidence_pages": [1, 5]
}}

The criterion_assessments array must contain an assessment
for EVERY supplied inclusion and exclusion criterion.

Use a page number only when the evidence is found on that
page. Use null for page when no supporting passage is available.

The evidence_pages array must contain only unique page
numbers actually present in the supplied evidence."""
    ),
    (
        "human",
        """Review topic:
{topic}

Research question:
{research_question}

Inclusion criteria:
{inclusion_criteria}

Exclusion criteria:
{exclusion_criteria}

Paper title:
{title}

Full-text evidence:
{full_text_evidence}

Assess this paper's eligibility."""
    )
])


eligibility_chain = eligibility_prompt | llm | parser


# EVIDENCE EXTRACTION PROMPT

evidence_extraction_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an academic evidence extraction assistant
supporting a systematic literature review.

Your task is to identify explicit evidence relevant to the
provided inclusion and exclusion criteria in the supplied
full-text pages.

RULES:

- Examine all supplied pages carefully.
- Extract only evidence relevant to at least one criterion.
- Preserve the exact page number where the evidence appears.
- Associate each evidence item with the exact criterion it supports.
- Do not make an overall eligibility decision.
- Do not conclude that a criterion is unmet merely because
  the supplied pages do not discuss it.
- Do not infer information that is not explicitly stated.
- Do not use outside knowledge.
- If no relevant evidence is found, return an empty list.

Return valid JSON with exactly this key:

{{
    "evidence_items": [
        {{
            "criterion": "Exact eligibility criterion",
            "evidence": "Relevant evidence from the paper",
            "page": 5
        }}
    ]
}}"""
    ),
    (
        "human",
        """Review topic:
{topic}

Research question:
{research_question}

Inclusion criteria:
{inclusion_criteria}

Exclusion criteria:
{exclusion_criteria}

Paper title:
{title}

Full-text pages:
{pages}

Extract relevant evidence."""
    )
])


# HELPERS

def get_paper_key(paper):
    """Generate a stable identifier for matching previous assessments."""

    return (
        paper.get("openalex_id")
        or paper.get("doi")
        or paper.get("crossref_id")
        or (paper.get("title") or "").strip().lower()
    )


def is_rate_limit_error(error):
    """Identify provider rate-limit errors, including Groq token limits."""

    message = str(error).lower()

    status_code = getattr(error, "status_code", None)

    response = getattr(error, "response", None)

    if response is not None:
        status_code = status_code or getattr(
            response, "status_code", None
        )

    return (
        status_code == 429
        or "429" in message
        or "rate limit" in message
        or "too many requests" in message
        or "tokens per day" in message
        or "tokens per minute" in message
        or "requests per minute" in message
        or "tpm" in message
        or "tpd" in message
    )


def is_completed_assessment(result):
    """Check whether a previous assessment can safely be reused."""

    reason = str(result.get("reason", "")).lower()

    technical_failure_indicators = [
        "assessment could not be completed",
        "no relevant full-text passages could be retrieved",
        "full-text pdf is unavailable",
        "no extracted full-text pages were found",
        "no readable full-text content was available",
        "rate limit",
        "error code: 429"
    ]

    if any(
        indicator in reason
        for indicator in technical_failure_indicators
    ):
        return False

    status = result.get("assessment_status")

    if status == "completed":
        return True

    if status in ["error", "retrieval_failed", "not_assessed"]:
        return False

    return result.get("decision") in [
        "Include",
        "Exclude",
        "Uncertain"
    ]


# EXTRACTED FULL-TEXT PAGES

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def load_extracted_pages(pdf_path):
    """Load all extracted pages for a given PDF."""

    target_filename = Path(
        str(pdf_path).replace("\\", "/")
    ).name.lower()

    for json_path in PROCESSED_DIR.glob("*.json"):

        try:
            with open(json_path, "r", encoding="utf-8") as file:
                paper_data = json.load(file)

            source_pdf = paper_data.get("source_pdf", "")

            source_filename = Path(
                source_pdf.replace("\\", "/")
            ).name.lower()

            if source_filename != target_filename:
                continue

            pages = paper_data.get("pages", [])

            if not pages:
                return []

            return sorted(
                pages,
                key=lambda page: page.get("page_number", 0)
            )

        except (json.JSONDecodeError, OSError) as error:

            print(
                f"[Eligibility] Could not read "
                f"{json_path}: {error}"
            )

    return []


# ASSESS ONE PAPER

def assess_paper_full_text(paper, retriever, protocol, topic):
    """Assess one paper using evidence extracted from all full-text pages."""

    pdf_path = paper.get("pdf_path")

    # Check whether the PDF exists.
    if not pdf_path or not os.path.isfile(pdf_path):

        return {
            "decision": None,
            "assessment_status": "retrieval_failed",
            "reason": "The full-text PDF is unavailable.",
            "evidence_pages": []
        }

    filename = os.path.basename(pdf_path)

    inclusion = protocol.get("inclusion_criteria") or []
    exclusion = protocol.get("exclusion_criteria") or []

    research_question = protocol.get(
        "research_question", "Not specified"
    )

    inclusion_text = "\n".join(
        f"- {criterion}" for criterion in inclusion
    )

    exclusion_text = "\n".join(
        f"- {criterion}" for criterion in exclusion
    )

    # Load extracted pages.
    pages = load_extracted_pages(pdf_path)

    if not pages:

        return {
            "decision": None,
            "assessment_status": "retrieval_failed",
            "reason": "No extracted full-text pages were found.",
            "evidence_pages": []
        }

    # Ensure the extracted pages contain readable text.
    if not any(
        str(page.get("text") or "").strip()
        for page in pages
    ):

        return {
            "decision": None,
            "assessment_status": "retrieval_failed",
            "reason": "No readable full-text content was available.",
            "evidence_pages": []
        }

    print(
        f"[Eligibility] Loaded {len(pages)} pages from {filename}"
    )

    # OPTIMIZATION: LOCAL RAG EVIDENCE SELECTION

    pages_for_llm = pages

    use_rag = os.getenv(
        "ELIGIBILITY_RAG_ENABLED", "1"
    ) == "1"

    if use_rag and len(pages) > 12:

        criteria = [
            str(c).strip()
            for c in inclusion + exclusion
            if str(c).strip()
        ]

        # Search for criterion-specific and methodological evidence.
        queries = criteria + [
            "Research methodology, study design, dataset and sample",
            "Main results, findings and conclusions"
        ]

        try:
            page_lookup = {
                int(page["page_number"]): page
                for page in pages
            }

            retrieved_groups = []

            for query in queries:

                results = retriever.search(
                    query=query,
                    top_k=3,
                    source_pdf=filename
                )

                if not results:
                    raise ValueError(
                        "No indexed passages for a query"
                    )

                retrieved_groups.append(results)

            selected_numbers = []

            def add_page(number):
                try:
                    number = int(number)
                except (TypeError, ValueError):
                    return

                if (
                    number in page_lookup
                    and number not in selected_numbers
                ):
                    selected_numbers.append(number)

            # Keep the opening pages and the final page.
            for page in pages[:2]:
                add_page(page["page_number"])

            add_page(pages[-1]["page_number"])

            # Preserve the highest-ranked hit for every query.
            for results in retrieved_groups:
                add_page(results[0].get("page_number"))

            max_pages = max(12, len(queries) + 3)

            # Add additional relevant pages.
            for rank in range(1, 3):

                for results in retrieved_groups:

                    if len(selected_numbers) >= max_pages:
                        break

                    if rank < len(results):
                        add_page(
                            results[rank].get("page_number")
                        )

            # Use RAG only if sufficient page coverage exists.
            # Otherwise, retain the original full-text approach.
            if len(selected_numbers) >= 6:

                pages_for_llm = sorted(
                    [
                        page_lookup[number]
                        for number in selected_numbers
                    ],
                    key=lambda page: page["page_number"]
                )

                print(
                    f"[Eligibility] RAG selected "
                    f"{len(pages_for_llm)}/{len(pages)} pages "
                    f"for {filename}"
                )

            else:
                print(
                    "[Eligibility] Insufficient RAG coverage. "
                    "Using all pages."
                )

        except Exception as error:

            print(
                "[Eligibility] RAG selection unavailable. "
                "Using all pages:",
                type(error).__name__
            )

            pages_for_llm = pages

    # Preserve the existing batch size and workflow.
    batch_size = 3

    page_batches = [
        pages_for_llm[i:i + batch_size]
        for i in range(0, len(pages_for_llm), batch_size)
    ]
    
    
    all_evidence = []

    # Extract evidence from every batch.
    for batch_number, batch in enumerate(page_batches, start=1):

        batch_text = "\n\n".join(
            f"[PAGE {page['page_number']}]\n{page['text']}"
            for page in batch
            if str(page.get("text") or "").strip()
        )

        if not batch_text.strip():
            continue

        print(
            f"[Eligibility] Processing batch {batch_number}/"
            f"{len(page_batches)} ({filename})"
        )

        print(
            f"[Eligibility] Batch {batch_number}: "
            f"{len(batch_text)} characters"
        )

        try:

            batch_input = {
                "topic": topic,
                "research_question": research_question,
                "inclusion_criteria": inclusion_text or "Not specified",
                "exclusion_criteria": exclusion_text or "Not specified",
                "title": paper.get("title", "Unavailable"),
                "pages": batch_text
            }

            prompt_value = evidence_extraction_prompt.invoke(
                batch_input
            )

            max_retries = 2

            for attempt in range(max_retries + 1):

                try:

                    raw_response = llm.invoke(prompt_value)

                    batch_result = parser.invoke(raw_response)

                    break

                except Exception as error:

                    if (
                        is_rate_limit_error(error)
                        and attempt < max_retries
                    ):

                        wait_time = 6 * (attempt + 1)

                        print(
                            f"[Eligibility] Rate limit reached. "
                            f"Retrying in {wait_time} seconds..."
                        )

                        time.sleep(wait_time)

                    else:
                        raise

        except Exception as error:

            print(
                f"[Eligibility] Batch {batch_number} failed: {error}"
            )

            raise RuntimeError(
                f"Evidence extraction failed for batch "
                f"{batch_number}/{len(page_batches)}: {error}"
            ) from error

        evidence_items = batch_result.get("evidence_items", [])

        if not isinstance(evidence_items, list):

            raise ValueError(
                "Invalid evidence extraction output."
            )

        # Validate evidence page numbers against this batch.
        valid_batch_pages = {
            page["page_number"]
            for page in batch
            if page.get("page_number") is not None
        }

        for item in evidence_items:

            if not isinstance(item, dict):
                continue

            try:
                page_number = int(item.get("page"))
            except (ValueError, TypeError):
                continue

            if page_number not in valid_batch_pages:
                continue

            criterion = str(
                item.get("criterion") or ""
            ).strip()

            evidence = str(
                item.get("evidence") or ""
            ).strip()

            if not criterion or not evidence:
                continue

            all_evidence.append({
                "criterion": criterion,
                "evidence": evidence,
                "page": page_number
            })

    print(
        f"[Eligibility] Extracted {len(all_evidence)} evidence items "
        f"from {filename}"
    )

    # Remove duplicate evidence items.
    unique_evidence = {}

    for item in all_evidence:

        key = (
            item["criterion"].lower(),
            item["page"],
            item["evidence"].lower()
        )

        unique_evidence[key] = item

    all_evidence = list(unique_evidence.values())

    # Prepare consolidated evidence for the final assessment.
    if all_evidence:

        evidence_text = "\n\n".join(
            (
                f"Criterion: {item['criterion']}\n"
                f"[PAGE {item['page']}]\n"
                f"{item['evidence']}"
            )
            for item in all_evidence
        )

    else:

        evidence_text = (
            "No relevant evidence was identified during "
            "the examination of the extracted full text."
        )

    # Make the final eligibility decision.
    result = eligibility_chain.invoke({
        "topic": topic,
        "research_question": research_question,
        "inclusion_criteria": inclusion_text or "Not specified",
        "exclusion_criteria": exclusion_text or "Not specified",
        "title": paper.get("title", "Unavailable"),
        "full_text_evidence": evidence_text
    })

    if not isinstance(result, dict):
        raise ValueError("Invalid final eligibility assessment output.")

    inclusion_set = {
        criterion.strip().lower()
        for criterion in inclusion
    }

    exclusion_set = {
        criterion.strip().lower()
        for criterion in exclusion
    }

    criterion_assessments = result.get(
        "criterion_assessments", []
    )

    if not isinstance(criterion_assessments, list):
        criterion_assessments = []

    for assessment in criterion_assessments:

        if not isinstance(assessment, dict):
            continue

        criterion = str(
            assessment.get("criterion") or ""
        ).strip().lower()

        if criterion in inclusion_set:
            assessment["type"] = "Inclusion"

        elif criterion in exclusion_set:
            assessment["type"] = "Exclusion"

    decision = str(
        result.get("decision", "Uncertain")
    ).strip().capitalize()

    if decision not in ["Include", "Exclude", "Uncertain"]:
        decision = "Uncertain"

    # Validate final evidence pages against the extracted paper.
    available_pages = {
        page["page_number"]
        for page in pages
        if page.get("page_number") is not None
    }

    reported_pages = result.get("evidence_pages", [])

    if not isinstance(reported_pages, list):
        reported_pages = [reported_pages]

    evidence_pages = []

    for page in reported_pages:

        try:
            page_number = int(page)

            if page_number in available_pages:
                evidence_pages.append(page_number)

        except (ValueError, TypeError):
            continue

    # Also include pages associated with extracted evidence.
    evidence_pages.extend(
        item["page"] for item in all_evidence
    )

    return {
        "decision": decision,
        "assessment_status": "completed",
        "reason": result.get(
            "reason",
            "No eligibility explanation provided."
        ),
        "criterion_assessments": criterion_assessments,
        "evidence_pages": sorted(set(evidence_pages))
    }


# FULL-TEXT ELIGIBILITY AGENT

def run_full_text_eligibility_agent(state):
    """Assess full-text papers while preserving completed results."""

    print("\n[Eligibility Agent] Starting full-text assessment...")

    papers = state.get("full_text_available_papers", [])
    protocol = state.get("protocol", {})

    previous_results = state.get(
        "full_text_assessment_results", []
    )

    previous_by_key = {
        get_paper_key(result): result
        for result in previous_results
        if get_paper_key(result)
    }

    assessment_results = []

    eligible_papers = []
    excluded_papers = []
    uncertain_papers = []

    error_papers = []
    retrieval_failed_papers = []
    pending_papers = []

    # No papers available.
    if not papers:

        print("[Eligibility Agent] No full-text papers available.")

        return {
            "full_text_assessment_results": [],
            "full_text_eligible_papers": [],
            "full_text_excluded_papers": [],
            "full_text_uncertain_papers": [],
            "full_text_error_papers": [],
            "full_text_retrieval_failed_papers": [],
            "full_text_pending_papers": [],
            "current_stage": "eligibility_completed",
            "execution_logs": add_execution_logs(
                state.get("execution_logs", []),
                "Full-text eligibility completed: no PDFs were available for assessment."
            )
        }

    # Initialize RAG.
    try:

        retriever = PaperRetriever()

    except Exception as error:

        print(
            "[Eligibility Agent] Could not initialize RAG:",
            error
        )

        failed_papers = [
            {
                **paper,
                "full_text_error": str(error)
            }
            for paper in papers
        ]

        return {
            "full_text_assessment_results": previous_results,
            "full_text_eligible_papers": state.get(
                "full_text_eligible_papers", []
            ),
            "full_text_excluded_papers": state.get(
                "full_text_excluded_papers", []
            ),
            "full_text_uncertain_papers": state.get(
                "full_text_uncertain_papers", []
            ),
            "full_text_error_papers": failed_papers,
            "full_text_retrieval_failed_papers": [],
            "full_text_pending_papers": [],
            "current_stage": "eligibility_failed",
            "execution_logs": add_execution_logs(
                state.get("execution_logs", []),
                f"Full-text eligibility failed during RAG initialization: {error}"
            )
        }

    stop_processing = False
    rate_limit_reached = False

    # Process each paper.
    for index, paper in enumerate(papers, 1):

        title = paper.get("title", "Untitled")
        paper_key = get_paper_key(paper)

        previous = previous_by_key.get(paper_key)

        # Reuse valid completed assessments.
        if previous and is_completed_assessment(previous):

            assessment = previous.copy()

            print(
                f"\n[Eligibility Agent] Reusing previous assessment: "
                f"{title}"
            )

        # Stop further LLM requests after a rate-limit failure.
        elif stop_processing:

            assessment = {
                "decision": None,
                "assessment_status": "not_assessed",
                "reason": (
                    "Not assessed because processing stopped "
                    "after a rate-limit error."
                ),
                "evidence_pages": []
            }

        else:

            print(
                f"\n[Eligibility Agent] Assessing paper "
                f"{index}/{len(papers)}: {title}"
            )

            try:

                assessment = assess_paper_full_text(
                    paper,
                    retriever,
                    protocol,
                    state.get("topic", "Not specified")
                )

            except Exception as error:

                print(
                    f"[Eligibility Agent] Assessment failed for "
                    f"{title}: {error}"
                )

                assessment = {
                    "decision": None,
                    "assessment_status": "error",
                    "reason": str(error),
                    "evidence_pages": []
                }

                if is_rate_limit_error(error):

                    print(
                        "[Eligibility Agent] Rate limit detected. "
                        "Stopping further LLM requests."
                    )

                    stop_processing = True
                    rate_limit_reached = True

        # Store the assessment result.
        record = {
            "title": title,
            "openalex_id": paper.get("openalex_id"),
            "doi": paper.get("doi"),
            "crossref_id": paper.get("crossref_id"),
            **assessment
        }

        assessment_results.append(record)

        status = assessment.get("assessment_status")

        # Classify the assessment.
        if status == "completed":

            decision = assessment.get("decision")

            if decision == "Include":

                eligible_papers.append(paper)

            elif decision == "Exclude":

                excluded_papers.append({
                    **paper,
                    "full_text_exclusion_reason": assessment.get(
                        "reason", ""
                    )
                })

            else:

                uncertain_papers.append({
                    **paper,
                    "full_text_uncertainty_reason": assessment.get(
                        "reason", ""
                    )
                })

        elif status == "retrieval_failed":

            retrieval_failed_papers.append({
                **paper,
                "full_text_retrieval_error": assessment.get(
                    "reason", "Full-text retrieval failed."
                )
            })

        elif status == "error":

            error_papers.append({
                **paper,
                "full_text_error": assessment.get(
                    "reason", "Technical assessment error."
                )
            })

        else:

            pending_papers.append(paper)

        print(
            "[Eligibility Agent] Status:",
            status,
            "| Decision:",
            assessment.get("decision", "Not assessed")
        )

        if assessment.get("reason"):
            print(
                "[Eligibility Agent] Reason:",
                assessment["reason"]
            )

    # Preserve previous completed assessments that are not in the
    # current full-text paper list.
    current_keys = {
        get_paper_key(paper)
        for paper in papers
    }

    for previous in previous_results:

        key = get_paper_key(previous)

        if (
            key not in current_keys
            and is_completed_assessment(previous)
        ):

            assessment_results.append(previous)

    # Eligibility is incomplete if any paper has not been
    # successfully assessed, including retrieval failures.
    incomplete = bool(
        error_papers
        or retrieval_failed_papers
        or pending_papers
    )

    current_stage = (
        "eligibility_partial"
        if incomplete
        else "eligibility_completed"
    )

    # Summary.
    print("\n[Eligibility Agent] Assessment summary.")

    print("Included:", len(eligible_papers))
    print("Excluded:", len(excluded_papers))
    print("Uncertain:", len(uncertain_papers))
    print("Assessment errors:", len(error_papers))
    print("Retrieval failures:", len(retrieval_failed_papers))
    print("Not assessed:", len(pending_papers))

    log_messages = [
        f"Full-text papers available: {len(papers)}.",
        f"Eligible after full-text assessment: {len(eligible_papers)}.",
        f"Excluded after full-text assessment: {len(excluded_papers)}.",
        f"Uncertain after full-text assessment: {len(uncertain_papers)}.",
        f"Technical assessment errors: {len(error_papers)}.",
        f"Full-text retrieval failures: {len(retrieval_failed_papers)}.",
        f"Papers not assessed: {len(pending_papers)}."
    ]

    if rate_limit_reached:

        log_messages.append(
            "Processing stopped because the LLM provider rate limit "
            "was reached. Failed and pending papers require a later retry."
        )

    if incomplete:

        log_messages.append(
            "Full-text eligibility is incomplete. "
            "The workflow must not proceed to extraction."
        )

    return {
        "full_text_assessment_results": assessment_results,
        "full_text_eligible_papers": eligible_papers,
        "full_text_excluded_papers": excluded_papers,
        "full_text_uncertain_papers": uncertain_papers,
        "full_text_error_papers": error_papers,
        "full_text_retrieval_failed_papers": retrieval_failed_papers,
        "full_text_pending_papers": pending_papers,
        "current_stage": current_stage,
        "execution_logs": add_execution_logs(
            state.get("execution_logs", []),
            log_messages
        )
    }
