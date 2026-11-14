import os
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from workflow.state import ReviewState
from agents.protocol_agent import generate_protocol
from agents.search_agent import run_search_agent
from agents.screening_agent import run_screening_agent
from agents.extraction_agent import prepare_full_text_documents, run_extraction_agent
from agents.appraisal_agent import run_appraisal_agent
from agents.synthesis_agent import run_synthesis_agent
from agents.critic_agent import run_critic_agent
from agents.full_text_eligibility_agent import run_full_text_eligibility_agent
from tools.prisma_tracker import calculate_prisma_data
from tools.prisma_diagram import generate_prisma_diagram
from tools.report_generator import generate_review_report
from server.utils.logging import add_execution_logs

def coordinator(state: ReviewState):
    topic = state.get("topic", "Unknown topic")
    print(f"\n[Coordinator] Starting review for: {topic}")

    return {
        "current_stage": "initialized",
        "execution_logs": add_execution_logs(state.get("execution_logs", []),
            [f"Review initialized for topic: {topic}"])
    }


def protocol_node(state: ReviewState):
    print("\n[Coordinator] Calling Protocol Agent...")

    protocol = generate_protocol(state["topic"])

    return {
        "protocol": protocol,
        "research_question": protocol["research_question"],
        "inclusion_criteria": protocol["inclusion_criteria"],
        "exclusion_criteria": protocol["exclusion_criteria"],
        "current_stage": "protocol_generated",
        "execution_logs": add_execution_logs(state.get("execution_logs", []),
            ["Review protocol generated successfully."])
    }


def search_node(state: ReviewState):
    print("\n[Coordinator] Calling Search Agent...")
    return run_search_agent(state)

def screening_node(state: ReviewState):
    print("\n[Coordinator] Calling Screening Agent...")
    return run_screening_agent(state)

def human_review_node(state: ReviewState):
    uncertain_papers = state.get("uncertain_papers", [])

    interrupt_payload = {
        "message": (
            "Review the dual-screening results. Approve or reject the "
            "screening, and resolve disagreements or uncertain papers."
        ),
        "screening_agreement": state.get("screening_agreement", {}),
        "screening_disagreements": [
            {
                "screening_paper_id": p.get("screening_paper_id"),
                "openalex_id": p.get("openalex_id"),
                "doi": p.get("doi"),
                "title": p.get("title"),
                "reviewer_assessments": p.get("reviewer_assessments", {}),
                "screening_reason": p.get("screening_reason"),
            }
            for p in state.get("screening_disagreements", [])
        ],
        "included_papers": [
            {
                "screening_paper_id": p.get("screening_paper_id"),
                "title": p.get("title"),
                "reason": p.get("screening_reason"),
            }
            for p in state.get("included_papers", [])
        ],
        "excluded_papers": [
            {
                "screening_paper_id": p.get("screening_paper_id"),
                "title": p.get("title"),
                "reason": p.get("screening_reason"),
            }
            for p in state.get("excluded_papers", [])
        ],
        "uncertain_papers": [
            {
                "screening_paper_id": p.get("screening_paper_id"),
                "openalex_id": p.get("openalex_id"),
                "doi": p.get("doi"),
                "title": p.get("title"),
                "reason": p.get("screening_reason"),
                "dual_screening_status": p.get("dual_screening_status"),
                "reviewer_assessments": p.get("reviewer_assessments", {}),
            }
            for p in uncertain_papers
        ],
    }

    decision = interrupt(interrupt_payload)

    if isinstance(decision, dict):
        approved = decision.get("approved", False)
        uncertain_decisions = decision.get("uncertain_decisions", {})
    else:
        approved = str(decision).strip().lower() in [
            "yes", "y", "true", "approve"
        ]
        uncertain_decisions = {}

    if not isinstance(uncertain_decisions, dict):
        uncertain_decisions = {}

    # Copy the screening results before applying human decisions.
    screening_results = [
        dict(paper)
        for paper in state.get("screening_results", [])
    ]

    adjudication_results = list(
        state.get("screening_adjudication_results", [])
    )

    resolved_decisions = {}

    for paper in uncertain_papers:
        paper_id = (
            paper.get("screening_paper_id")
            or paper.get("openalex_id")
            or paper.get("doi")
            or paper.get("title")
        )

        title = paper.get("title")

        human_decision = (
            uncertain_decisions.get(paper_id)
            or uncertain_decisions.get(str(paper_id))
            or uncertain_decisions.get(title)
            or "Uncertain"
        )

        human_decision = str(human_decision).strip().capitalize()

        if human_decision not in ["Include", "Exclude", "Uncertain"]:
            human_decision = "Uncertain"

        if human_decision in ["Include", "Exclude"]:
            resolved_decisions[str(paper_id)] = human_decision

            adjudication_results.append({
                "screening_paper_id": paper_id,
                "openalex_id": paper.get("openalex_id"),
                "doi": paper.get("doi"),
                "title": title,
                "reviewer_assessments": paper.get(
                    "reviewer_assessments", {}
                ),
                "human_decision": human_decision,
                "human_reason": (
                    "Decision made during human adjudication."
                ),
                "previous_status": paper.get(
                    "dual_screening_status"
                ),
            })

    # Apply decisions to the master screening results.
    for paper in screening_results:
        paper_id = (
            paper.get("screening_paper_id")
            or paper.get("openalex_id")
            or paper.get("doi")
            or paper.get("title")
        )

        human_decision = resolved_decisions.get(str(paper_id))

        if human_decision:
            paper["screening_decision"] = human_decision
            paper["screening_reason"] = (
                f"{human_decision} following human adjudication."
            )
            paper["human_adjudicated"] = True

    # Rebuild the decision groups from the updated results.
    included = [
        p for p in screening_results
        if p.get("screening_decision") == "Include"
    ]

    excluded = [
        p for p in screening_results
        if p.get("screening_decision") == "Exclude"
    ]

    uncertain = [
        p for p in screening_results
        if p.get("screening_decision") == "Uncertain"
    ]

    unresolved_disagreements = [
        p for p in uncertain
        if p.get("dual_screening_status") == "needs_adjudication"
    ]

    logs = add_execution_logs(
        state.get("execution_logs", []),
        (
            "Human Review: Human review completed. "
            f"{len(resolved_decisions)} papers adjudicated; "
            f"{len(unresolved_disagreements)} disagreements "
            f"remain unresolved. Approval: {approved}."
        )
    )

    return {
        "human_approval": bool(approved),
        "screening_results": screening_results,
        "included_papers": included,
        "excluded_papers": excluded,
        "uncertain_papers": uncertain,
        "screening_adjudication_results": adjudication_results,
        "current_stage": (
            "screening_approved"
            if approved
            else "screening_needs_revision"
        ),
        "execution_logs": logs,
    }

def pdf_preparation_node(state: ReviewState):
    print("\n[Coordinator] Preparing full-text documents...")
    return prepare_full_text_documents(state)


def full_text_eligibility_node(state: ReviewState):
    print("\n[Coordinator] Calling Full-Text Eligibility Agent...")
    return run_full_text_eligibility_agent(state)

def extraction_node(state: ReviewState):
    print("\n[Coordinator] Calling Extraction Agent...")
    return run_extraction_agent(state)

def approval_router(state: ReviewState):
    if state.get("human_approval") is True:
        return "pdf_preparation"
    return END

def extraction_router(state: ReviewState):
    status = state.get("extraction_status")
    if status == "completed":
        return "appraisal"

    if status == "skipped":
        return "prisma"

    # Do not proceed with incomplete or failed extraction.
    print(
        f"[Coordinator] Extraction is {status}. "
        "Stopping the workflow before quality appraisal."
    )
    return END

def appraisal_node(state: ReviewState):
    print("\n[Coordinator] Calling Appraisal Agent...")
    return run_appraisal_agent(state)

def synthesis_node(state: ReviewState):
    print("\n[Coordinator] Calling Synthesis Agent...")
    return run_synthesis_agent(state)

def critic_node(state: ReviewState):
    print("\n[Coordinator] Calling Critic Agent...")
    return run_critic_agent(state)

def prisma_node(state: ReviewState):
    print("\n[Coordinator] Calculating PRISMA statistics...")
    prisma_data = calculate_prisma_data(state)
    print("[PRISMA] Statistics calculated.")
    return {
        "prisma_data": prisma_data,
        "execution_logs": add_execution_logs(state.get("execution_logs", []), [
            "PRISMA statistics calculated."
        ])
    }

def prisma_diagram_node(state: ReviewState):
    print("\n[Coordinator] Generating PRISMA diagram...")
    output_path = generate_prisma_diagram(state.get("prisma_data", {}))
    return {
        "prisma_diagram_path": output_path,
        "execution_logs": add_execution_logs(state.get("execution_logs", []), [
            "PRISMA flow diagram generated successfully."
        ])
    }

def report_node(state: ReviewState):
    print("\n[Coordinator] Generating final review report...")
    report_path = generate_review_report(state)
    return {
        "final_report": report_path,
        "current_stage": "report_generated",
        "execution_logs": add_execution_logs(state.get("execution_logs", []), [
            "Systematic review report generated successfully."
        ])
    }

builder = StateGraph(ReviewState)

builder.add_node("coordinator", coordinator)
builder.add_node("protocol", protocol_node)
builder.add_node("search", search_node)
builder.add_node("screening", screening_node)
builder.add_node("pdf_preparation", pdf_preparation_node)
builder.add_node("full_text_eligibility", full_text_eligibility_node)
builder.add_node("human_review", human_review_node)
builder.add_node("extract", extraction_node)
builder.add_node("appraisal", appraisal_node)
builder.add_node("synthesis", synthesis_node)
builder.add_node("critic", critic_node)
builder.add_node("prisma", prisma_node)
builder.add_node("prisma_diagram", prisma_diagram_node)
builder.add_node("report", report_node)

# Main workflow
builder.add_edge(START, "coordinator")
builder.add_edge("coordinator", "protocol")
builder.add_edge("protocol", "search")
builder.add_edge("search", "screening")
builder.add_edge("screening", "human_review")
builder.add_conditional_edges("human_review", approval_router, {"pdf_preparation": "pdf_preparation", END: END})
builder.add_edge("pdf_preparation", "full_text_eligibility")
builder.add_edge("full_text_eligibility", "extract")
builder.add_conditional_edges("extract", extraction_router, {"appraisal": "appraisal", "prisma": "prisma", END: END})
builder.add_edge("appraisal", "synthesis")
builder.add_edge("synthesis", "critic")
builder.add_edge("critic", "prisma")
builder.add_edge("prisma", "prisma_diagram")
builder.add_edge("prisma_diagram", "report")
builder.add_edge("report", END)

os.makedirs("data", exist_ok=True)

connection = sqlite3.connect(
    "data/review_checkpoints.sqlite",
    check_same_thread=False
)

checkpointer = SqliteSaver(connection)
checkpointer.setup()

review_graph = builder.compile(checkpointer=checkpointer)