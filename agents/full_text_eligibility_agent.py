
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from config.llm import get_llm
from rag.retriever import PaperRetriever

import os


llm = get_llm()
parser = JsonOutputParser()


eligibility_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an academic full-text eligibility assessor
conducting a systematic literature review.

Assess the supplied research paper against the approved
inclusion and exclusion criteria.

DECISION RULES:

1. Include:
   The available full-text evidence clearly supports the
   paper meeting the relevant inclusion criteria, with no
   identified exclusion criterion.

2. Exclude:
   The full text provides clear evidence that the paper
   violates at least one exclusion criterion or fails a
   mandatory inclusion criterion.

3. Uncertain:
   The available evidence is insufficient, ambiguous, or
   does not allow a reliable eligibility decision.

IMPORTANT RULES:

- Base your decision on the supplied full-text passages.
- Do not assume that a criterion is satisfied merely
  because the available passages do not contradict it.
- Do not infer missing information.
- Distinguish between information not reported and
  evidence that a criterion is not met.
- If the evidence is insufficient, choose Uncertain.
- Explain the decision clearly and concisely.
- Identify the page numbers supporting your decision.
- Do not use information from other papers.
- Do not treat the abstract alone as full-text evidence.

Return valid JSON with exactly these keys:

{
    "decision": "Include, Exclude, or Uncertain",
    "reason": "Explanation of the eligibility decision.",
    "evidence_pages": [1, 3]
}"""
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

Full-text passages:
{full_text_evidence}

Assess this paper's eligibility."""
    )
])


eligibility_chain = eligibility_prompt | llm | parser


def assess_paper_full_text(paper, retriever, protocol):
    """Assess one paper using its retrieved full-text passages."""

    pdf_path = paper.get("pdf_path")

    if not pdf_path or not os.path.isfile(pdf_path):
        return {
            "decision": "Uncertain",
            "reason": "The full-text PDF is unavailable.",
            "evidence_pages": []
        }

    filename = os.path.basename(pdf_path)

    inclusion = protocol.get("inclusion_criteria", [])
    exclusion = protocol.get("exclusion_criteria", [])

    inclusion_text = "\n".join(
        f"- {criterion}" for criterion in inclusion
    )

    exclusion_text = "\n".join(
        f"- {criterion}" for criterion in exclusion
    )

    query = (
        "Assess this study against the following systematic review "
        "eligibility criteria. Study population, research objectives, "
        "methodology, study design, outcomes, and exclusion conditions. "
        + " ".join(inclusion)
        + " "
        + " ".join(exclusion)
    )

    passages = retriever.search(
        query,
        top_k=10,
        source_pdf=filename
    )

    if not passages:
        return {
            "decision": "Uncertain",
            "reason": "No relevant full-text passages could be retrieved.",
            "evidence_pages": []
        }

    evidence_text = "\n\n".join(
        f"[PAGE {passage['page_number']}]\n{passage['text']}"
        for passage in passages
    )

    result = eligibility_chain.invoke({
        "topic": protocol.get("topic", "Not specified"),
        "research_question": protocol.get(
            "research_question", "Not specified"
        ),
        "inclusion_criteria": inclusion_text or "Not specified",
        "exclusion_criteria": exclusion_text or "Not specified",
        "title": paper.get("title", "Unavailable"),
        "full_text_evidence": evidence_text
    })

    decision = str(result.get("decision", "Uncertain")).strip().capitalize()

    if decision not in ["Include", "Exclude", "Uncertain"]:
        decision = "Uncertain"

    return {
        "decision": decision,
        "reason": result.get(
            "reason", "No eligibility explanation provided."
        ),
        "evidence_pages": result.get("evidence_pages", [])
    }


def run_full_text_eligibility_agent(state):
    """Assess all successfully processed full-text papers."""

    print("\n[Eligibility Agent] Starting full-text assessment...")

    papers = state.get("full_text_available_papers", [])
    protocol = state.get("protocol", {})

    assessment_results = []
    eligible_papers = []
    excluded_papers = []
    uncertain_papers = []

    if not papers:
        print("[Eligibility Agent] No full-text papers available.")

        return {
            "full_text_assessment_results": [],
            "full_text_eligible_papers": [],
            "full_text_excluded_papers": [],
            "full_text_uncertain_papers": [],
            "current_stage": "eligibility_completed",
            "execution_logs": state.get("execution_logs", []) + [
                "Full-text eligibility completed: no PDFs were available for assessment."
            ]
        }

    try:
        retriever = PaperRetriever()
    except Exception as error:
        print("[Eligibility Agent] Could not initialize RAG:", error)

        return {
            "full_text_assessment_results": [],
            "full_text_eligible_papers": [],
            "full_text_excluded_papers": [],
            "full_text_uncertain_papers": [],
            "current_stage": "eligibility_failed",
            "execution_logs": state.get("execution_logs", []) + [
                f"Full-text eligibility failed: {error}"
            ]
        }

    for index, paper in enumerate(papers, 1):

        title = paper.get("title", "Untitled")

        print(
            f"\n[Eligibility Agent] Assessing paper "
            f"{index}/{len(papers)}: {title}"
        )

        try:
            assessment = assess_paper_full_text(
                paper,
                retriever,
                protocol
            )

        except Exception as error:
            print(
                f"[Eligibility Agent] Assessment failed for "
                f"{title}: {error}"
            )

            assessment = {
                "decision": "Uncertain",
                "reason": f"Assessment could not be completed: {error}",
                "evidence_pages": []
            }

        record = {
            "title": title,
            "openalex_id": paper.get("openalex_id"),
            **assessment
        }

        assessment_results.append(record)

        if assessment["decision"] == "Include":
            eligible_papers.append(paper)

        elif assessment["decision"] == "Exclude":
            excluded_papers.append({
                **paper,
                "full_text_exclusion_reason": assessment["reason"]
            })

        else:
            uncertain_papers.append({
                **paper,
                "full_text_uncertainty_reason": assessment["reason"]
            })

        print("[Eligibility Agent] Decision:", assessment["decision"])
        print("[Eligibility Agent] Reason:", assessment["reason"])

    print("\n[Eligibility Agent] Assessment completed.")
    print("Included:", len(eligible_papers))
    print("Excluded:", len(excluded_papers))
    print("Uncertain:", len(uncertain_papers))

    return {
        "full_text_assessment_results": assessment_results,
        "full_text_eligible_papers": eligible_papers,
        "full_text_excluded_papers": excluded_papers,
        "full_text_uncertain_papers": uncertain_papers,
        "current_stage": "eligibility_completed",
        "execution_logs": state.get("execution_logs", []) + [
            f"Full-text papers assessed: {len(assessment_results)}.",
            f"Eligible after full-text assessment: {len(eligible_papers)}.",
            f"Excluded after full-text assessment: {len(excluded_papers)}.",
            f"Uncertain after full-text assessment: {len(uncertain_papers)}."
        ]
    }
