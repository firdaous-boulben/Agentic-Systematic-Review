
import json
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from config.llm import get_llm

load_dotenv()

llm = get_llm()

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an academic systematic review quality-control specialist.

Your task is to critically evaluate a research synthesis
generated from extracted academic studies.

Evaluate the synthesis using the approved review protocol,
research question, extracted evidence, and quality appraisal.

ASSESSMENT DIMENSIONS:

1. Evidence consistency:
   Are the claims supported by the extracted information?
   Are numerical results and study findings accurately represented?

2. Source traceability:
   Are important findings attributed to identifiable studies?
   Are study titles and publication years accurate when available?

3. Unsupported claims:
   Are there invented, exaggerated, or insufficiently supported statements?

4. Study classification:
   Are primary studies distinguished from systematic reviews
   and other review studies?

5. Methodological interpretation:
   Are research methods, datasets, evaluation approaches,
   and findings interpreted accurately?

6. Quality appraisal:
   Does the synthesis reflect the available quality assessment?
   Are methodological weaknesses and strengths interpreted appropriately?

7. Research question coverage:
   Does the synthesis address the research question and objectives?

8. Research gaps:
   Are identified gaps supported by the available evidence?

9. Limitations:
   Are missing information, incomplete extraction, and evidence limitations acknowledged?

10. Academic quality:
    Is the synthesis coherent, critical, logically organized,
    and appropriately cautious?

IMPORTANT RULES:

- Use only the supplied information.
- Do not introduce external facts.
- Do not assume that information absent from an abstract
  is absent from the full paper.
- Distinguish full-text extraction from abstract-only extraction.
- Do not treat missing appraisal results as evidence of poor quality.
- Do not treat review conclusions as independent experimental findings.
- Identify specific claims or sections that need correction.
- Do not approve a synthesis simply because it is well written.
- If evidence is insufficient to verify a claim, explicitly state this.
- Evaluate the synthesis according to the actual research topic.
- Do not expect predefined sections or methods specific to another domain.

VERDICT:

Return APPROVED only if the synthesis is sufficiently supported,
accurate, and aligned with the research question.

Return NEEDS_REVISION if important claims are unsupported,
important evidence is misrepresented, or significant limitations
are not acknowledged.

Return your assessment using this structure:

VERDICT: APPROVED or NEEDS_REVISION

STRENGTHS:
- ...

ISSUES:
- ...

RECOMMENDATIONS:
- ...

OVERALL ASSESSMENT:
A short explanation of your verdict."""
    ),
    (
        "human",
        """Research topic: {topic}

Research question: {research_question}

Approved review protocol:
{protocol_data}

Topic-specific extraction dimensions:
{extraction_dimensions}

Extracted evidence:
{extracted_data}

Quality appraisal:
{quality_results}

Generated synthesis:
{synthesis}

Evaluate the synthesis."""
    )
])

critic_chain = prompt | llm


def run_critic_agent(state):
    print("\\n[Critic Agent] Reviewing research synthesis...")

    synthesis = state.get("synthesis", "")

    if not synthesis:
        return {
            "critic_feedback": "No synthesis available for evaluation.",
            "validation_status": "needs_revision",
            "current_stage": "critic_failed",
            "execution_logs": state.get("execution_logs", []) + [
                "Critic evaluation skipped: no synthesis available."
            ]
        }

    protocol = state.get("protocol", {})

    protocol_summary = {
        "research_question": protocol.get("research_question"),
        "objectives": protocol.get("objectives", []),
        "inclusion_criteria": protocol.get("inclusion_criteria", []),
        "extraction_dimensions": protocol.get(
            "extraction_dimensions", []
        )
    }

    response = critic_chain.invoke({
        "topic": state.get("topic", ""),
        "research_question": state.get(
            "research_question",
            protocol.get("research_question", "")
        ),
        "protocol_data": json.dumps(
            protocol_summary,
            indent=2,
            ensure_ascii=False
        ),
        "extraction_dimensions": json.dumps(
            protocol.get("extraction_dimensions", []),
            indent=2,
            ensure_ascii=False
        ),
        "extracted_data": json.dumps(
            state.get("extracted_data", []),
            indent=2,
            ensure_ascii=False
        ),
        "quality_results": json.dumps(
            state.get("quality_results", []),
            indent=2,
            ensure_ascii=False
        ),
        "synthesis": synthesis
    })

    feedback = response.content

    if "VERDICT: APPROVED" in feedback.upper():
        status = "approved"
    else:
        status = "needs_revision"

    print(f"\\n[Critic Agent] Evaluation completed: {status}")

    return {
        "critic_feedback": feedback,
        "validation_status": status,
        "current_stage": "critic_completed",
        "execution_logs": state.get("execution_logs", []) + [
            f"Critic evaluation completed: {status}."
        ]
    }
