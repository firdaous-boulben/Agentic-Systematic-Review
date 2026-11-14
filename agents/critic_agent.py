
import json
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from config.llm import get_llm

from server.utils.logging import add_execution_logs

load_dotenv()

# Keep the critic's response concise.
llm = get_llm(max_tokens=3000)


def compact_value(value, max_chars=250, max_items=4):
    """Limit the size of nested information."""

    if isinstance(value, str):
        return value[:max_chars] + ("..." if len(value) > max_chars else "")

    if isinstance(value, list):
        return [
            compact_value(item, max_chars, max_items)
            for item in value[:max_items]
        ]

    if isinstance(value, dict):
        return {
            key: compact_value(item, max_chars, max_items)
            for key, item in value.items()
        }

    return value


def compact_extraction(paper):
    information = paper.get("extracted_information", {})

    if not isinstance(information, dict):
        information = {}

    return {
        "title": paper.get("title"),
        "year": paper.get("year"),
        "study_type": compact_value(
            information.get("study_type", ""),
            max_chars=100
        ),
        "research_objective": compact_value(
            information.get("research_objective", ""),
            max_chars=150
        ),
        "main_findings": compact_value(
            information.get("main_findings", ""),
            max_chars=300
        ),
        "limitations": compact_value(
            information.get("limitations", ""),
            max_chars=150
        )
    }


def compact_appraisal(result):
    """Keep the actual quality assessments, without unnecessary details."""

    appraisal = result.get("quality_appraisal", result)

    if not isinstance(appraisal, dict):
        return {
            "title": result.get("title"),
            "assessment": compact_value(appraisal)
        }

    return {
        "title": result.get("title"),
        "study_type": appraisal.get("study_type"),
        "assessments": compact_value(
            appraisal.get("assessments", {}),
            max_chars=200
        ),
        "overall_judgment": compact_value(
            appraisal.get("overall_judgment", ""),
            max_chars=250
        )
    }


prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an academic systematic review quality-control specialist.

Critically evaluate the generated synthesis using the approved protocol,
extracted study summaries, supporting evidence references, and quality appraisal.

ASSESSMENT DIMENSIONS:

1. Evidence consistency: Are claims supported by the extracted information?
2. Source traceability: Are findings attributed to identifiable studies?
3. Unsupported claims: Are statements exaggerated or insufficiently supported?
4. Study classification: Are primary studies distinguished from review studies?
5. Methodological interpretation: Are methods and findings interpreted accurately?
6. Quality appraisal: Does the synthesis reflect the available appraisal?
7. Research question coverage: Does it address the research question and objectives?
8. Research gaps: Are identified gaps supported by the evidence?
9. Limitations: Are evidence limitations acknowledged?
10. Academic quality: Is the synthesis coherent, critical, and appropriately cautious?

IMPORTANT RULES:

- Use only the supplied information.
- Do not introduce external facts.
- Do not assume information absent from an abstract is absent from the full paper.
- Distinguish full-text extraction from abstract-only extraction.
- Do not treat review conclusions as independent experimental findings.
- Do not treat missing appraisal results as evidence of poor quality.
- Do not invent evidence or references.
- If evidence is insufficient to verify a claim, state this explicitly.
- Do not approve a synthesis simply because it is well written.

Keep your evaluation concise (maximum 250 words).

Do not provide lengthy explanations or repeat the synthesis.

Include:
- Two or three strengths.
- Only the most important issues.
- Specific recommendations.
- A brief overall assessment.

Do not output your internal reasoning. Return only the requested evaluation.

VERDICT:

Return APPROVED only if the synthesis is sufficiently supported,
accurate, and aligned with the research question.

Return NEEDS_REVISION if important claims are unsupported,
misrepresented, or insufficiently qualified.

Use exactly this structure:

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

Approved protocol:
{protocol_data}

Extracted study summaries:
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
    print("\n[Critic Agent] Reviewing research synthesis...")

    synthesis = state.get("synthesis", "")

    if not synthesis:
        return {
            "critic_feedback": "No synthesis available for evaluation.",
            "validation_status": "needs_revision",
            "current_stage": "critic_failed",
            "execution_logs": add_execution_logs(
                state.get("execution_logs", []),
                "Critic evaluation skipped: no synthesis available."
            )
        }

    protocol = state.get("protocol", {})

    protocol_summary = {
        "research_question": protocol.get("research_question"),
        "objectives": compact_value(
            protocol.get("objectives", []),
            max_chars=200
        ),
        "inclusion_criteria": compact_value(
            protocol.get("inclusion_criteria", []),
            max_chars=150
        ),
        "extraction_dimensions": compact_value(
            protocol.get("extraction_dimensions", []),
            max_chars=150
        )
    }

    extracted_data = [
        compact_extraction(paper)
        for paper in state.get("extracted_data", [])
    ]

    quality_results = [
        compact_appraisal(result)
        for result in state.get("quality_results", [])
    ]

    payload = {
        "topic": state.get("topic", ""),
        "research_question": state.get(
            "research_question",
            protocol.get("research_question", "")
        ),
        "protocol_data": json.dumps(
            protocol_summary,
            ensure_ascii=False
        ),
        "extracted_data": json.dumps(
            extracted_data,
            ensure_ascii=False
        ),
        "quality_results": json.dumps(
            quality_results,
            ensure_ascii=False
        ),
        "synthesis": synthesis
    }

    total_chars = sum(
        len(str(value))
        for value in payload.values()
    )

    print(f"[Critic Agent] Input size: {total_chars:,} characters")

    response = critic_chain.invoke(payload)

    print("\n========== CRITIC DEBUG ==========")
    print("FULL RESPONSE:", repr(response))
    print("CONTENT:", repr(response.content))
    print("RESPONSE METADATA:", response.response_metadata)
    print("ADDITIONAL KWARGS:", response.additional_kwargs)
    print("USAGE METADATA:", response.usage_metadata)
    print("==================================\n")

    content = response.content

    print("[Critic Agent] Response type:", type(content))
    print("[Critic Agent] Raw response:", repr(content)[:3000])

    if isinstance(content, str):
        feedback = content

    elif isinstance(content, list):
        parts = []

        for block in content:
            if isinstance(block, str):
                parts.append(block)

            elif isinstance(block, dict):
                text = block.get("text") or block.get("content")

                if isinstance(text, str):
                    parts.append(text)

            else:
                text = getattr(block, "text", None)

                if isinstance(text, str):
                    parts.append(text)

        feedback = "\n".join(parts)

    else:
        feedback = str(content)

    feedback = feedback.strip()

    if not feedback:
        raise ValueError(
            "Critic Agent returned an empty response. "
            "Check the raw response printed above."
        )

    if "VERDICT: APPROVED" in feedback.upper():
        status = "approved"
    else:
        status = "needs_revision"

    print(f"\n[Critic Agent] Evaluation completed: {status}")

    return {
        "critic_feedback": feedback,
        "validation_status": status,
        "current_stage": "critic_completed",
        "execution_logs": add_execution_logs(
            state.get("execution_logs", []),
            f"Critic evaluation completed: {status}."
        )
    }
