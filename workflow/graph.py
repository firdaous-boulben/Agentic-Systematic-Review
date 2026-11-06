from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
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

def coordinator(state: ReviewState):
    topic = state.get("topic", "Unknown topic")
    print(f"\n[Coordinator] Starting review for: {topic}")

    return {
        "current_stage": "initialized",
        "execution_logs": state.get("execution_logs", []) +
            [f"Review initialized for topic: {topic}"]
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
        "execution_logs": state.get("execution_logs", []) +
            ["Review protocol generated successfully."]
    }


def search_node(state: ReviewState):
    print("\n[Coordinator] Calling Search Agent...")
    return run_search_agent(state)

def screening_node(state: ReviewState):
    print("\n[Coordinator] Calling Screening Agent...")
    return run_screening_agent(state)

def human_review_node(state: ReviewState):

    decision = interrupt({
        "message": (
            "Review the screening results. Approve or reject the screening, "
            "and resolve uncertain papers where possible."
        ),

        "included_papers": [
            {"title": p["title"], "reason": p["screening_reason"]}
            for p in state.get("included_papers", [])
        ],

        "excluded_papers": [
            {"title": p["title"], "reason": p["screening_reason"]}
            for p in state.get("excluded_papers", [])
        ],

        "uncertain_papers": [
            {
                "title": p["title"],
                "openalex_id": p.get("openalex_id"),
                "reason": p["screening_reason"]
            }
            for p in state.get("uncertain_papers", [])
        ]
    })

    # Support both a simple approval and detailed human decisions.
    if isinstance(decision, dict):
        approved = decision.get("approved", False)
        uncertain_decisions = decision.get("uncertain_decisions", {})
    else:
        approved = str(decision).lower() in ["yes", "y", "true", "approve"]
        uncertain_decisions = {}

    included = list(state.get("included_papers", []))
    excluded = list(state.get("excluded_papers", []))
    uncertain = []

    for paper in state.get("uncertain_papers", []):
        paper_id = paper.get("openalex_id")
        paper_title = paper.get("title")

        human_decision = (
            uncertain_decisions.get(paper_id)
            or uncertain_decisions.get(paper_title)
            or "Uncertain"
        )

        human_decision = str(human_decision).strip().lower()

        if human_decision == "include":
            paper["screening_decision"] = "Include"
            paper["screening_reason"] = (
                "Included following human review."
            )
            included.append(paper)

        elif human_decision == "exclude":
            paper["screening_decision"] = "Exclude"
            paper["screening_reason"] = (
                "Excluded following human review."
            )
            excluded.append(paper)

        else:
            paper["screening_decision"] = "Uncertain"
            uncertain.append(paper)

    return {
        "human_approval": bool(approved),
        "included_papers": included,
        "excluded_papers": excluded,
        "uncertain_papers": uncertain,
        "current_stage": (
            "screening_approved"
            if approved
            else "screening_needs_revision"
        ),
        "execution_logs": state.get("execution_logs", []) + [
            f"Human screening approval: {approved}",
            f"Uncertain papers resolved: "
            f"{len(state.get('uncertain_papers', [])) - len(uncertain)}",
            f"Papers remaining uncertain: {len(uncertain)}"
        ]
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
        "execution_logs": state.get("execution_logs", []) + [
            "PRISMA statistics calculated."
        ]
    }

def prisma_diagram_node(state: ReviewState):
    print("\n[Coordinator] Generating PRISMA diagram...")
    output_path = generate_prisma_diagram(state.get("prisma_data", {}))
    return {
        "prisma_diagram_path": output_path,
        "execution_logs": state.get("execution_logs", []) + [
            "PRISMA flow diagram generated successfully."
        ]
    }

def report_node(state: ReviewState):
    print("\n[Coordinator] Generating final review report...")
    report_path = generate_review_report(state)
    return {
        "final_report": report_path,
        "current_stage": "report_generated",
        "execution_logs": state.get("execution_logs", []) + [
            "Systematic review report generated successfully."
        ]
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
# Human review of title/abstract screening
builder.add_edge("screening", "human_review")
# Continue only if the screening is approved
builder.add_conditional_edges("human_review", approval_router, {"pdf_preparation": "pdf_preparation", END: END})
# Full-text retrieval and eligibility
builder.add_edge("pdf_preparation", "full_text_eligibility")
builder.add_edge("full_text_eligibility", "extract")
# Information extraction and analysis
builder.add_edge("extract", "appraisal")
builder.add_edge("appraisal", "synthesis")
builder.add_edge("synthesis", "critic")
# Final PRISMA statistics and report
builder.add_edge("critic", "prisma")
builder.add_edge("prisma", "prisma_diagram")
builder.add_edge("prisma_diagram", "report")
builder.add_edge("report", END)

memory = MemorySaver()
review_graph = builder.compile(checkpointer=memory)