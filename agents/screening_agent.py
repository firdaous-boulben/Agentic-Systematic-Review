
import os
import json
import hashlib
import re
from pathlib import Path
from collections import Counter

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from config.llm import get_llm
from server.utils.logging import add_execution_logs


load_dotenv()

llm = get_llm()
parser = JsonOutputParser()

BATCH_SIZE = 5
CACHE_PATH = Path("data/processed/screening_cache.json")
PROMPT_VERSION = "dual-review-v3-compact"

VALID_DECISIONS = {"Include", "Exclude", "Uncertain"}


# Cache

def load_screening_cache():
    if not CACHE_PATH.exists():
        return {}

    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}


def save_screening_cache(cache):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(CACHE_PATH, "w", encoding="utf-8") as file:
        json.dump(cache, file, indent=2, ensure_ascii=False)


def get_cache_key(paper, state, reviewer_id):
    """
    Generates a reviewer-specific cache key.

    Reviewer A and Reviewer B must never reuse each other's
    assessments. Prompt versioning also prevents reuse of
    assessments generated with previous prompts.
    """

    data = {
        "reviewer": reviewer_id,
        "prompt_version": PROMPT_VERSION,
        "paper_id": get_paper_id(paper, 0),
        "title": paper.get("title", ""),
        "abstract": paper.get("abstract", ""),
        "topic": state.get("topic", ""),
        "research_question": state.get("research_question", ""),
        "inclusion_criteria": state.get("inclusion_criteria", []),
        "exclusion_criteria": state.get("exclusion_criteria", []),
        "publication_year_range": (
            state.get("protocol", {}).get("publication_year_range")
            if isinstance(state.get("protocol"), dict)
            else None
        ),
        "model": os.getenv("GROQ_MODEL", ""),
    }

    serialized = json.dumps(
        data,
        sort_keys=True,
        ensure_ascii=False
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()

def is_rate_limit_error(error):
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
        or "tpm" in message
        or "tpd" in message
    )


# Paper utilities

def get_paper_id(paper, index):
    return (
        paper.get("openalex_id")
        or paper.get("doi")
        or paper.get("title")
        or f"paper_{index}"
    )
def is_standalone_figure(paper):
    """
    Identify standalone figure records, not research papers.

    Conservative rule:
    - Crossref type must be 'component'.
    - Title must explicitly begin with Figure or Fig.
    """

    paper_type = str(
        paper.get("type") or ""
    ).strip().lower()

    title = " ".join(
        str(paper.get("title") or "").split()
    )

    return (
        paper_type == "component"
        and bool(
            re.match(
                r"^(?:Figure|Fig\.?)\s*\d",
                title,
                flags=re.IGNORECASE
            )
        )
    )

def check_publication_year(paper, state):
    """
    Returns:
        True  -> year is within the configured range
        False -> year is outside the configured range
        None  -> no reliable year/range check is possible
    """

    protocol = state.get("protocol", {})

    if not isinstance(protocol, dict):
        return None

    year_range = protocol.get("publication_year_range")

    if not year_range:
        return None

    year = paper.get("year")

    try:
        year = int(year)
    except (TypeError, ValueError):
        return None

    try:
        if isinstance(year_range, dict):
            start = year_range.get("start")
            end = year_range.get("end")

        elif isinstance(year_range, (list, tuple)) and len(year_range) == 2:
            start, end = year_range

        else:
            return None

        start = int(start) if start is not None else None
        end = int(end) if end is not None else None

        if start is not None and year < start:
            return False

        if end is not None and year > end:
            return False

        return True

    except (TypeError, ValueError):
        return None


# Shared input structure for both reviewers
SCREENING_HUMAN_PROMPT = """
Research topic: {topic}
Research question: {research_question}
Inclusion criteria: {inclusion_criteria}
Exclusion criteria: {exclusion_criteria}

Papers:
{papers_json}

Assess every paper.
Return exactly one result per supplied paper_id.
"""


# Reviewer A: Strict eligibility assessment
reviewer_a_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are Reviewer A, an independent title and abstract screener.

Apply all supplied inclusion and exclusion criteria.

Rules:
- Include: All required criteria are supported by the evidence.
- Exclude: Evidence clearly violates at least one criterion.
- Uncertain: Evidence is insufficient to establish eligibility.

Do not invent missing information.
Use only the supplied paper information.
Give a brief evidence-based reason (maximum 20 words).

Return ONLY valid JSON:
{{
  "results": [
    {{
      "paper_id": "ID",
      "decision": "Include",
      "reason": "Brief evidence-based justification"
    }}
  ]
}}
"""
    ),
    ("human", SCREENING_HUMAN_PROMPT)
])


# Reviewer B: Independent relevance assessment
reviewer_b_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are Reviewer B, an independent academic screener.

Apply the same supplied inclusion and exclusion criteria.
Focus on research relevance and available evidence.

Rules:
- Include: Available evidence supports eligibility.
- Exclude: Evidence clearly demonstrates a criterion violation.
- Uncertain: Important details are missing or require full-text review.

Do not reject a paper simply because its abstract is incomplete.
Do not invent methods, outcomes, or missing information.
Give a brief evidence-based reason (maximum 20 words).

Return ONLY valid JSON:
{{
  "results": [
    {{
      "paper_id": "ID",
      "decision": "Include",
      "reason": "Brief evidence-based justification"
    }}
  ]
}}
"""
    ),
    ("human", SCREENING_HUMAN_PROMPT)
])


# Each reviewer has a separate chain and prompt.
reviewer_a_chain = reviewer_a_prompt | llm | parser
reviewer_b_chain = reviewer_b_prompt | llm | parser


# One reviewer assessment

def assess_batch(batch, state, reviewer_id, cache):
    """
    Runs one reviewer's assessment for a batch.

    Returns:
        paper_id -> decision, reason and assessment status.
    """

    results = {}
    uncached_papers = []

    for paper, index in batch:
        paper_id = get_paper_id(paper, index)
        cache_key = get_cache_key(paper, state, reviewer_id)

        cached_result = cache.get(cache_key)

        if (
            isinstance(cached_result, dict)
            and cached_result.get("decision") in VALID_DECISIONS
        ):
            results[paper_id] = {
                "decision": cached_result["decision"],
                "reason": cached_result.get("reason", ""),
                "status": "completed",
                "cached": True,
                "rate_limit": False,
            }

        else:
            uncached_papers.append(
                (paper, index, paper_id, cache_key)
            )

    if not uncached_papers:
        return results

    papers_payload = [
        {
            "paper_id": paper_id,
            "title": paper.get("title", ""),
            "abstract": paper.get("abstract", ""),
            "year": paper.get("year"),
            "type": paper.get("type", []),
            "journal": paper.get("journal", ""),
        }
        for paper, _, paper_id, _ in uncached_papers
    ]

    if reviewer_id == "reviewer_a":
        chain = reviewer_a_chain
    elif reviewer_id == "reviewer_b":
        chain = reviewer_b_chain
    else:
        raise ValueError(
            f"Unknown reviewer identity: {reviewer_id}"
        )

    payload = {
        "topic": state.get("topic", ""),
        "research_question": state.get("research_question", ""),
        "inclusion_criteria": json.dumps(
            state.get("inclusion_criteria", []),
            ensure_ascii=False
        ),
        "exclusion_criteria": json.dumps(
            state.get("exclusion_criteria", []),
            ensure_ascii=False
        ),
        "papers_json": json.dumps(
            papers_payload,
            ensure_ascii=False
        ),
    }

    max_retries = 2
    rate_limit_reached = False

    for attempt in range(max_retries + 1):

        try:
            response = chain.invoke(payload)

            if not isinstance(response, dict):
                raise ValueError(
                    "Invalid screening response format."
                )

            returned_results = response.get("results", [])

            if not isinstance(returned_results, list):
                raise ValueError(
                    "The screening response has no valid results list."
                )

            returned_by_id = {
                str(item.get("paper_id")): item
                for item in returned_results
                if (
                    isinstance(item, dict)
                    and item.get("paper_id") is not None
                )
            }

            for _, _, paper_id, cache_key in uncached_papers:

                item = returned_by_id.get(str(paper_id))

                if not item:
                    results[paper_id] = {
                        "decision": None,
                        "reason": (
                            "The reviewer did not return a result "
                            "for this paper."
                        ),
                        "status": "technical_error",
                        "cached": False,
                        "rate_limit": False,
                    }
                    continue

                decision = str(
                    item.get("decision", "")
                ).strip().capitalize()

                reason = str(
                    item.get("reason", "")
                ).strip()

                if decision not in VALID_DECISIONS:
                    results[paper_id] = {
                        "decision": None,
                        "reason": (
                            "The reviewer returned an invalid "
                            "screening decision."
                        ),
                        "status": "technical_error",
                        "cached": False,
                        "rate_limit": False,
                    }
                    continue

                if not reason:
                    reason = (
                        "No justification was provided by the reviewer."
                    )

                reviewer_result = {
                    "decision": decision,
                    "reason": reason,
                    "status": "completed",
                    "cached": False,
                    "rate_limit": False,
                }

                results[paper_id] = reviewer_result

                cache[cache_key] = {
                    "decision": decision,
                    "reason": reason,
                }

            save_screening_cache(cache)

            return results

        except Exception as error:

            if is_rate_limit_error(error):

                if attempt < max_retries and "tokens per day" not in str(error).lower():

                    wait_time = 6 * (attempt + 1)

                    print(
                        f"[Screening Agent] {reviewer_id} "
                        f"rate limit reached. Retrying in "
                        f"{wait_time} seconds..."
                    )

                    import time
                    time.sleep(wait_time)

                    continue

                rate_limit_reached = True

            print(
                f"[Screening Agent] {reviewer_id} "
                f"assessment failed: {error}"
            )

            for _, _, paper_id, _ in uncached_papers:
                results[paper_id] = {
                    "decision": None,
                    "reason": str(error),
                    "status": "technical_error",
                    "cached": False,
                    "rate_limit": rate_limit_reached,
                }

            return results

    return results


# Agreement calculation

def calculate_screening_agreement(dual_results):
    """
    Calculates observed agreement and Cohen's kappa.

    Includes every paper successfully assessed by both reviewers,
    including disagreements requiring human adjudication.

    Excludes papers with technical errors or without two
    successful assessments.
    """

    valid_pairs = [
        item
        for item in dual_results
        if item.get("dual_screening_status") in [
            "assessed",
            "needs_adjudication"
        ]
    ]

    total = len(valid_pairs)

    if total == 0:
        return {
            "assessed_pairs": 0,
            "agreements": 0,
            "disagreements": 0,
            "agreement_percentage": None,
            "cohens_kappa": None,
            "note": (
                "No papers received two valid reviewer assessments."
            ),
        }

    reviewer_a = [
        item["reviewer_assessments"]["reviewer_a"]["decision"]
        for item in valid_pairs
    ]

    reviewer_b = [
        item["reviewer_assessments"]["reviewer_b"]["decision"]
        for item in valid_pairs
    ]

    agreements = sum(
        a == b
        for a, b in zip(reviewer_a, reviewer_b)
    )

    disagreements = total - agreements

    observed_agreement = agreements / total

    categories = ["Include", "Exclude", "Uncertain"]

    count_a = Counter(reviewer_a)
    count_b = Counter(reviewer_b)

    expected_agreement = sum(
        (count_a[category] / total)
        * (count_b[category] / total)
        for category in categories
    )

    if expected_agreement == 1:
        kappa = None
        note = (
            "Cohen's kappa is undefined because the expected "
            "agreement is 1."
        )

    else:
        kappa = (
            observed_agreement - expected_agreement
        ) / (1 - expected_agreement)

        note = None

    return {
        "assessed_pairs": total,
        "agreements": agreements,
        "disagreements": disagreements,
        "agreement_percentage": round(
            observed_agreement * 100, 2
        ),
        "cohens_kappa": (
            round(kappa, 4)
            if kappa is not None
            else None
        ),
        "note": note,
    }


# Final decision from two reviewers

def combine_reviewer_assessments(paper, paper_id, reviewer_a, reviewer_b):
    assessments = {
        "reviewer_a": reviewer_a,
        "reviewer_b": reviewer_b,
    }

    both_completed = (
        reviewer_a.get("status") == "completed"
        and reviewer_b.get("status") == "completed"
    )

    result = {
        **paper,
        "screening_paper_id": paper_id,
        "reviewer_assessments": assessments,
    }

    if not both_completed:
        result.update({
            "screening_decision": None,
            "screening_reason": (
                "At least one reviewer assessment failed technically. "
                "The paper requires reassessment."
            ),
            "dual_screening_status": "technical_error",
        })

        return result

    decision_a = reviewer_a["decision"]
    decision_b = reviewer_b["decision"]

    if decision_a == decision_b:
        result.update({
            "screening_decision": decision_a,
            "screening_reason": (
                f"Both reviewers agreed: {decision_a}. "
                f"Reviewer A: {reviewer_a['reason']} "
                f"Reviewer B: {reviewer_b['reason']}"
            ),
            "dual_screening_status": "assessed",
        })

        if decision_a == "Uncertain":
            result["screening_status"] = "needs_human_review"

        return result

    result.update({
        "screening_decision": "Uncertain",
        "screening_reason": (
            "The two reviewers disagreed. "
            "Human adjudication is required."
        ),
        "dual_screening_status": "needs_adjudication",
    })

    return result


# Main screening agent

def run_screening_agent(state, max_papers=None):
    print("\n[Screening Agent] Starting dual screening...")

    papers = state.get("unique_papers", [])

    if max_papers is not None:
        papers = papers[:max_papers]

    cache = load_screening_cache()

    reviewer_a_results = {}
    reviewer_b_results = {}

    prepared_papers = []
    deterministic_exclusions = []
    missing_abstracts = []

    # Prepare papers and apply deterministic year exclusions.
    for index, paper in enumerate(papers):
        paper_id = get_paper_id(paper, index)

        year_check = check_publication_year(paper, state)

        if year_check is False:
            deterministic_exclusions.append({
                **paper,
                "screening_paper_id": paper_id,
                "screening_decision": "Exclude",
                "screening_reason": (
                    "Publication year is outside the configured "
                    "publication year range."
                ),
                "dual_screening_status": "deterministic_exclusion",
            })

            continue
        
        # Symbolic screening: exclude standalone figures.
        # This requires no LLM calls.
        if is_standalone_figure(paper):

            deterministic_exclusions.append({
                **paper,
                "screening_paper_id": paper_id,
                "screening_decision": "Exclude",
                "screening_reason": (
                    "Standalone figure record, not a "
                    "complete research study."
                ),
                "dual_screening_status": "deterministic_exclusion",
            })

            continue

        if not paper.get("abstract"):
            missing_abstracts.append({
                **paper,
                "screening_paper_id": paper_id,
                "screening_decision": "Uncertain",
                "screening_reason": (
                    "No abstract is available for reliable title "
                    "and abstract screening. Manual assessment "
                    "is required."
                ),
                "dual_screening_status": "not_assessed",
            })

            continue

        prepared_papers.append((paper, index))

    # Run the two reviewers independently.
    stop_processing = False
    rate_limit_reached = False

    for start in range(0, len(prepared_papers), BATCH_SIZE):

        batch = prepared_papers[start:start + BATCH_SIZE]

        print(
            f"[Screening Agent] Processing batch "
            f"{start // BATCH_SIZE + 1}..."
        )

        reviewer_a_batch = assess_batch(
            batch,
            state,
            "reviewer_a",
            cache
        )

        reviewer_a_results.update(reviewer_a_batch)

        # Stop before calling Reviewer B if Reviewer A reached
        # the provider rate limit.
        if any(
            result.get("rate_limit")
            for result in reviewer_a_batch.values()
        ):
            stop_processing = True
            rate_limit_reached = True
            break

        reviewer_b_batch = assess_batch(
            batch,
            state,
            "reviewer_b",
            cache
        )

        reviewer_b_results.update(reviewer_b_batch)

        if any(
            result.get("rate_limit")
            for result in reviewer_b_batch.values()
        ):
            stop_processing = True
            rate_limit_reached = True
            break

    # Papers not processed because of a rate limit remain
    # without completed assessments and can be retried later.
    
    # Combine reviewer assessments.
    dual_screening_results = []
    screening_results = []

    for paper, index in prepared_papers:
        paper_id = get_paper_id(paper, index)

        reviewer_a = reviewer_a_results.get(paper_id, {
            "decision": None,
            "reason": "Reviewer A assessment was not completed.",
            "status": "technical_error",
            "cached": False,
        })

        reviewer_b = reviewer_b_results.get(paper_id, {
            "decision": None,
            "reason": "Reviewer B assessment was not completed.",
            "status": "technical_error",
            "cached": False,
        })

        combined = combine_reviewer_assessments(
            paper,
            paper_id,
            reviewer_a,
            reviewer_b
        )

        dual_screening_results.append(combined)
        screening_results.append(combined)

    # Include deterministic exclusions and missing abstracts.
    screening_results.extend(deterministic_exclusions)
    screening_results.extend(missing_abstracts)

    # Calculate final screening groups.
    included = [
        paper for paper in screening_results
        if paper.get("screening_decision") == "Include"
    ]

    excluded = [
        paper for paper in screening_results
        if paper.get("screening_decision") == "Exclude"
    ]

    uncertain = [
        paper for paper in screening_results
        if paper.get("screening_decision") == "Uncertain"
    ]

    disagreements = [
        paper for paper in uncertain
        if paper.get("dual_screening_status") == "needs_adjudication"
    ]

    agreement = calculate_screening_agreement(dual_screening_results)

    technical_failures = [
        paper for paper in screening_results
        if paper.get("dual_screening_status") == "technical_error"
    ]

    # A screening stage is incomplete if technical failures remain.
    screening_incomplete = bool(technical_failures)

    current_stage = (
        "screening_partial"
        if screening_incomplete
        else "screening_completed"
    )

    print(
        f"[Screening Agent] Completed: "
        f"{len(included)} included, "
        f"{len(excluded)} excluded, "
        f"{len(uncertain)} uncertain."
    )

    print(
        f"[Screening Agent] Agreement: "
        f"{agreement['agreement_percentage']}%"
        if agreement["agreement_percentage"] is not None
        else "[Screening Agent] Agreement could not be calculated."
    )

    logs = add_execution_logs(
        state.get("execution_logs", []),
        [
            (
                "Screening Agent: "
                f"{len(included)} included, "
                f"{len(excluded)} excluded, "
                f"{len(uncertain)} uncertain, "
                f"{len(disagreements)} disagreements."
            ),
            (
                f"Technical screening failures: "
                f"{len(technical_failures)}."
            ),
            (
                "Screening stopped because of a provider rate limit."
                if rate_limit_reached
                else "No provider rate limit interrupted screening."
            ),
            f"Screening stage: {current_stage}."
        ]
    )

    return {
        # Existing fields retained for compatibility.
        "screening_results": screening_results,
        "included_papers": included,
        "excluded_papers": excluded,
        "uncertain_papers": uncertain,

        # Dual-screening fields.
        "dual_screening_results": dual_screening_results,
        "screening_agreement": agreement,
        "screening_disagreements": disagreements,
        "screening_adjudication_results": [],

        "current_stage": current_stage,
        "execution_logs": logs,

        # Diagnostic information.
        "screening_technical_failures": technical_failures,
    }
