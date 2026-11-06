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
        """You are an academic methodological quality appraisal assistant.

Assess the methodological quality of the supplied academic paper
using only the available title, abstract, and extracted information.

Evaluate these dimensions:
1. objective_clarity
2. methodology
3. dataset_description
4. evaluation_methods
5. findings_transparency
6. reproducibility

For each dimension, assign one rating:
- High
- Moderate
- Low
- Insufficient Information

Rules:
- Do not invent methodological details.
- Missing information must be rated Insufficient Information.
- Do not confuse missing abstract information with poor quality.
- Provide a short justification for every rating.
- Do not calculate an overall score.
- Clearly identify information requiring full-text verification.

Return valid JSON with these keys:
{{
    "study_type": "...",
    "assessments": {{
        "objective_clarity": {{"rating": "...", "reason": "..."}},
        "methodology": {{"rating": "...", "reason": "..."}},
        "dataset_description": {{"rating": "...", "reason": "..."}},
        "evaluation_methods": {{"rating": "...", "reason": "..."}},
        "findings_transparency": {{"rating": "...", "reason": "..."}},
        "reproducibility": {{"rating": "...", "reason": "..."}}
    }},
    "full_text_verification": ["..."]
}}"""
    ),
    (
        "human",
        """Paper title: {title}

Abstract:
{abstract}

Extracted information:
{extracted_information}"""
    )
])

appraisal_chain = prompt | llm | parser


def appraise_paper(paper):
    result = appraisal_chain.invoke({
        "title": paper.get("title", "Unavailable"),
        "abstract": (paper.get("abstract") or "Unavailable")[:5000],
        "extracted_information": str(
            paper.get("extracted_information", {})
        )
    })

    return {
        **paper,
        "quality_appraisal": result
    }


def run_appraisal_agent(state):
    print("\n[Appraisal Agent] Starting quality assessment...")

    papers = state.get("extracted_data", [])
    quality_results = []

    for index, paper in enumerate(papers, 1):
        print(
            f"[Appraisal Agent] Assessing paper "
            f"{index}/{len(papers)}..."
        )

        try:
            result = appraise_paper(paper)
            quality_results.append(result)

        except Exception as error:
            print("[Appraisal Agent] Error:", error)

    print("\n[Appraisal Agent] Assessment completed.")
    print("Successfully assessed:", len(quality_results))

    return {
        "quality_results": quality_results,
        "current_stage": "appraisal_completed",
        "execution_logs": state.get("execution_logs", []) + [
            f"Appraised {len(quality_results)} papers."
        ]
    }