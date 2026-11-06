from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from config.llm import get_llm

load_dotenv()

llm = get_llm()

parser = JsonOutputParser()

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an academic screening assistant for systematic reviews.

Evaluate each paper using ONLY its title, abstract, and
the provided research topic and eligibility criteria.

Classify papers using these rules:

- Include: the available information clearly demonstrates
  that the paper satisfies the research topic and all
  relevant inclusion criteria.

- Exclude: the available information clearly demonstrates
  that the paper fails to satisfy at least one inclusion
  criterion or meets an exclusion criterion.

- Uncertain: the available information is insufficient
  to determine whether the paper meets the eligibility
  criteria. This includes missing or incomplete abstracts
  and unclear relevance to the research topic.

Important rules:
- Follow the provided criteria strictly.
- Do not introduce additional eligibility requirements.
- Do not assume that a paper satisfies a criterion without
  supporting evidence in its title or abstract.
- Do not exclude potentially relevant papers solely because
  their abstracts are unavailable.
- Do not invent information or research findings.
- Provide a short explanation for every decision.

Return valid JSON with these keys:
{{
    "decision": "Include, Exclude, or Uncertain",
    "reason": "Explanation of the decision"
}}"""
    ),
    (
        "human",
        """Research topic: {topic}

Inclusion criteria:
{inclusion_criteria}

Exclusion criteria:
{exclusion_criteria}

Paper title: {title}

Abstract:
{abstract}"""
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
        start_year, end_year = map(
            int, year_range.split("-")
        )
    except (ValueError, AttributeError):
        return None

    year = paper.get("year")

    if year is None:
        return None

    try:
        year = int(year)
    except (ValueError, TypeError):
        return None

    if year < start_year or year > end_year:
        return False

    return True

def screen_paper(paper, state):

    year_check = check_publication_year(paper, state)

    print(
        f"[Year Check] {paper.get('title')} | "
        f"Year: {paper.get('year')} | "
        f"Result: {year_check}"
    )

    if year_check is False:
        return {
            **paper,
            "screening_decision": "Exclude",
            "screening_reason": (
                f"Publication year ({paper.get('year')}) "
                "is outside the approved range."
            )
        }

    result = screening_chain.invoke({
        "topic": state["topic"],
        "inclusion_criteria": "\n".join(
            state["inclusion_criteria"]
        ),
        "exclusion_criteria": "\n".join(
            state["exclusion_criteria"]
        ),
        "title": paper.get("title") or "Unavailable",
        "abstract": (paper.get("abstract") or "Unavailable")[:5000]
    })

    decision = result.get("decision", "Uncertain").capitalize()

    if decision not in ["Include", "Exclude", "Uncertain"]:
        decision = "Uncertain"

    return {
        **paper,
        "screening_decision": decision,
        "screening_reason": result.get(
            "reason", "No explanation provided."
        )
    }


def run_screening_agent(state, max_papers=None):
    print("\n[Screening Agent] Starting paper screening...")

    papers = state.get("unique_papers", [])

    if max_papers is not None:
        papers = papers[:max_papers]

    screening_results = []

    for index, paper in enumerate(papers, 1):
        print(
            f"[Screening Agent] Screening paper "
            f"{index}/{len(papers)}..."
        )

        try:
            result = screen_paper(paper, state)
        except Exception as error:
            print(f"[Screening Agent] Error: {error}")

            result = {
                **paper,
                "screening_decision": "Uncertain",
                "screening_reason": "Screening failed; manual review required."
            }

        screening_results.append(result)

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

    print("\n[Screening Agent] Screening completed.")
    print("Included:", len(included))
    print("Excluded:", len(excluded))
    print("Uncertain:", len(uncertain))

    return {
        "screening_results": screening_results,
        "included_papers": included,
        "excluded_papers": excluded,
        "uncertain_papers": uncertain,
        "current_stage": "screening_completed",
        "execution_logs": state.get("execution_logs", []) + [
            f"Screened {len(screening_results)} papers.",
            f"Included: {len(included)}.",
            f"Excluded: {len(excluded)}.",
            f"Uncertain: {len(uncertain)}."
        ]
    }