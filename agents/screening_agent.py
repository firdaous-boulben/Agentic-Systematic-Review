import os
import json
import hashlib
from pathlib import Path
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


def load_screening_cache():
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

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
        json.dump(cache, file, indent=4, ensure_ascii=False)


def get_cache_key(paper, state):
    data = {
        "paper_id": get_paper_id(paper, 0),
        "title": paper.get("title"),
        "abstract": paper.get("abstract"),
        "topic": state.get("topic"),
        "inclusion_criteria": state.get("inclusion_criteria"),
        "exclusion_criteria": state.get("exclusion_criteria"),
        "model": os.getenv("GROQ_MODEL")
    }

    content = json.dumps(data, sort_keys=True, ensure_ascii=False)

    return hashlib.sha256(content.encode("utf-8")).hexdigest()

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an academic screening assistant for systematic reviews.

Evaluate each paper using ONLY its title, abstract, research topic,
and eligibility criteria.

Classify each paper as:
- Include: clearly satisfies the relevant inclusion criteria.
- Exclude: clearly fails at least one inclusion criterion or meets an exclusion criterion.
- Uncertain: information is insufficient, including missing or incomplete abstracts.

Rules:
- Follow the criteria strictly.
- Do not introduce additional requirements.
- Do not assume unsupported information.
- Do not exclude potentially relevant papers solely because their abstracts are unavailable.
- Do not invent information.
- Give a short reason for every decision.
- Evaluate every paper independently.
- Return exactly one result for each input paper.
- Preserve each paper's ID exactly.

Return valid JSON in this format:
{{
    "results": [
        {{
            "paper_id": "the exact paper ID",
            "decision": "Include, Exclude, or Uncertain",
            "reason": "Short explanation"
        }}
    ]
}}"""
    ),
    (
        "human",
        """Research topic: {topic}

Inclusion criteria:
{inclusion_criteria}

Exclusion criteria:
{exclusion_criteria}

Papers to evaluate:
{papers}"""
    )
])

screening_chain = prompt | llm | parser


def check_publication_year(paper, state):
    year_range = state.get("protocol", {}).get(
        "publication_year_range"
    )

    if not year_range:
        raise ValueError("Publication year range is missing from the protocol.")

    try:
        start_year, end_year = map(int, year_range.split("-"))
    except (ValueError, AttributeError):
        return None

    year = paper.get("year")

    if year is None:
        return None

    try:
        year = int(year)
    except (ValueError, TypeError):
        return None

    return start_year <= year <= end_year


def get_paper_id(paper, index):
    return (
        paper.get("openalex_id")
        or paper.get("doi")
        or paper.get("title")
        or f"paper_{index}"
    )


def screen_batch(batch, state, start_index):
    papers_to_evaluate = []
    results_by_id = {}
    cache = load_screening_cache()
    cache_keys = {}

    for offset, paper in enumerate(batch):
        index = start_index + offset
        paper_id = get_paper_id(paper, index)

        year_check = check_publication_year(paper, state)

        if year_check is False:
            results_by_id[paper_id] = {
                **paper,
                "screening_decision": "Exclude",
                "screening_status": "completed",
                "screening_reason": (
                    f"Publication year ({paper.get('year')}) "
                    "is outside the approved range."
                )
            }
            continue

        if not paper.get("abstract"):
            results_by_id[paper_id] = {
                **paper,
                "screening_decision": "Uncertain",
                "screening_status": "completed",
                "screening_reason": (
                    "Abstract unavailable; manual review required."
                )
            }
            continue

        cache_key = get_cache_key(paper, state)
        cache_keys[paper_id] = cache_key

        cached_result = cache.get(cache_key)

        if cached_result:
            print(f"[Screening Cache] Reusing: {paper.get('title')}")

            results_by_id[paper_id] = {
                **paper,
                "screening_decision": cached_result["decision"],
                "screening_status": "completed",
                "screening_reason": cached_result["reason"]
            }
        else:
            papers_to_evaluate.append({
                "paper_id": paper_id,
                "title": paper.get("title") or "Unavailable",
                "abstract": paper.get("abstract", "")[:3000]
            })

    if papers_to_evaluate:
        print(
            f"[Screening Agent] Sending "
            f"{len(papers_to_evaluate)} papers to the LLM..."
        )

        result = screening_chain.invoke({
            "topic": state["topic"],
            "inclusion_criteria": "\n".join(
                state["inclusion_criteria"]
            ),
            "exclusion_criteria": "\n".join(
                state["exclusion_criteria"]
            ),
            "papers": str(papers_to_evaluate)
        })

        returned_results = {
            item.get("paper_id"): item
            for item in result.get("results", [])
            if isinstance(item, dict)
        }

        for paper_data in papers_to_evaluate:
            paper_id = paper_data["paper_id"]

            original_paper = next(
                p for offset, p in enumerate(batch)
                if get_paper_id(p, start_index + offset) == paper_id
            )

            item = returned_results.get(paper_id)

            if not item:
                results_by_id[paper_id] = {
                    **original_paper,
                    "screening_decision": "Uncertain",
                    "screening_status": "technical_error",
                    "screening_reason": (
                        "No valid screening result returned; "
                        "manual review required."
                    )
                }
                continue

            decision = str(item.get("decision", "")).capitalize()

            if decision not in ["Include", "Exclude", "Uncertain"]:
                results_by_id[paper_id] = {
                    **original_paper,
                    "screening_decision": "Uncertain",
                    "screening_status": "technical_error",
                    "screening_reason": "Invalid LLM decision; manual review required."
                }
                continue

            reason = item.get("reason", "No explanation provided.")

            results_by_id[paper_id] = {
                **original_paper,
                "screening_decision": decision,
                "screening_status": "completed",
                "screening_reason": reason
            }

            # Cache only valid LLM decisions.
            cache[cache_keys[paper_id]] = {
                "decision": decision,
                "reason": reason
            }

        save_screening_cache(cache)

    return [
        results_by_id.get(
            get_paper_id(paper, start_index + offset),
            {
                **paper,
                "screening_decision": "Uncertain",
                "screening_status": "completed",
                "screening_reason": "Screening result missing; manual review required."
            }
        )
        for offset, paper in enumerate(batch)
    ]

def run_screening_agent(state, max_papers=None):
    print("\n[Screening Agent] Starting paper screening...")

    papers = state.get("unique_papers", [])

    if max_papers is not None:
        papers = papers[:max_papers]

    screening_results = []

    for start in range(0, len(papers), BATCH_SIZE):
        batch = papers[start:start + BATCH_SIZE]

        print(
            f"[Screening Agent] Screening batch "
            f"{start // BATCH_SIZE + 1}/"
            f"{(len(papers) + BATCH_SIZE - 1) // BATCH_SIZE}..."
        )

        try:
            batch_results = screen_batch(batch, state, start)
        except Exception as error:
            print(f"[Screening Agent] Batch error: {error}")

            batch_results = [
                {
                    **paper,
                    "screening_decision": "Uncertain",
                    "screening_status": "technical_error",
                    "screening_reason": (
                        f"Technical screening failure: {error}"
                    )
                }
                for paper in batch
            ]

        screening_results.extend(batch_results)

    completed = [
        p for p in screening_results
        if p.get("screening_status") == "completed"
    ]
    
    included = [
        p for p in screening_results
        if p["screening_decision"] == "Include"
    ]

    excluded = [
        p for p in screening_results
        if p["screening_decision"] == "Exclude"
    ]

    uncertain = [
        p for p in screening_results
        if p["screening_decision"] == "Uncertain"
    ]

    technical_failures = [
        p for p in screening_results
        if p.get("screening_status") == "technical_error"
    ]

    print("\n[Screening Agent] Screening completed.")
    print("Included:", len(included))
    print("Excluded:", len(excluded))
    print("Uncertain:", len(uncertain))
    print("Technical failures:", len(technical_failures))

    return {
        "screening_results": screening_results,
        "included_papers": included,
        "excluded_papers": excluded,
        "uncertain_papers": uncertain,
        "current_stage": "screening_completed",
        "execution_logs": add_execution_logs(
            state.get("execution_logs", []), 
            [
                f"Screened {len(screening_results)} papers in batches of {BATCH_SIZE}.",
                f"Included: {len(included)}.",
                f"Excluded: {len(excluded)}.",
                f"Uncertain: {len(uncertain)}."
            ]
        )
    }