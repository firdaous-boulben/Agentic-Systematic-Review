from uuid import uuid4
import sqlite3
from langgraph.types import Command
from workflow.graph import review_graph

def get_config(review_id: str):
    return {"configurable": {"thread_id": review_id}}


def start_review(review_id: str, topic: str):
    config = get_config(review_id)
    review_graph.invoke({"topic": topic}, config)


def resume_review(review_id: str, decision: dict):
    config = get_config(review_id)
    review_graph.invoke(Command(resume=decision), config)


def get_review(review_id: str):
    config = get_config(review_id)
    snapshot = review_graph.get_state(config)

    if not snapshot.values:
        return None

    state = snapshot.values

    if "human_review" in snapshot.next:
        status = "awaiting_human_review"

    elif state.get("current_stage") == "failed":
        status = "failed"

    elif (
        not snapshot.next
        and state.get("extraction_status") in [
            "partially_completed",
            "failed"
        ]
    ):
        status = "extraction_incomplete"

    elif not snapshot.next and state.get("final_report"):
        status = "completed"

    elif not snapshot.next:
        status = "stopped"

    else:
        status = "running"

    interrupt_data = []

    for task in snapshot.tasks:
        for item in getattr(task, "interrupts", []):
            interrupt_data.append(item.value)

    return {
        "review_id": review_id,
        "status": status,
        "topic": state.get("topic"),
        "research_question": state.get("research_question"),
        "protocol": state.get("protocol"),
        "current_stage": state.get("current_stage"),
        "execution_logs": state.get("execution_logs", []),
        "errors": state.get("errors", []),

        "retrieved_papers": state.get("retrieved_papers", []),
        "unique_papers": state.get("unique_papers", []),

        "screening_results": state.get("screening_results", []),
        "dual_screening_results": state.get("dual_screening_results", []),
        "screening_agreement": state.get("screening_agreement", {}),
        "screening_disagreements": state.get("screening_disagreements", []),
        "screening_adjudication_results": state.get(
            "screening_adjudication_results", []
        ),
        "screening_technical_failures": state.get(
            "screening_technical_failures", []
        ),
        "included_papers": state.get("included_papers", []),
        "excluded_papers": state.get("excluded_papers", []),
        "uncertain_papers": state.get("uncertain_papers", []),

        "pdf_retrieval_results": state.get("pdf_retrieval_results", []),
        "full_text_assessment_results": state.get(
            "full_text_assessment_results", []
        ),

        "extracted_data": state.get("extracted_data", []),
        "extraction_status": state.get("extraction_status"),
        "extraction_failures": state.get("extraction_failures", []),
        "quality_results": state.get("quality_results", []),

        "synthesis": state.get("synthesis"),
        "critic_feedback": state.get("critic_feedback"),
        "validation_status": state.get("validation_status"),

        "prisma_data": state.get("prisma_data", {}),
        "prisma_diagram_path": state.get("prisma_diagram_path"),
        "final_report": state.get("final_report"),

        "human_approval": state.get("human_approval"),
        "interrupt": interrupt_data,

        "next_nodes": list(snapshot.next),
    }

def get_all_checkpoint_reviews():
    connection = sqlite3.connect(
        "data/review_checkpoints.sqlite",
        check_same_thread=False
    )

    try:
        rows = connection.execute("""
            SELECT DISTINCT thread_id
            FROM checkpoints
            WHERE thread_id IS NOT NULL
        """).fetchall()

        reviews = []

        for (review_id,) in rows:
            review = get_review(review_id)

            if review:
                reviews.append(review)

        return reviews

    finally:
        connection.close()

def prepare_extraction_retry(review_id: str):
    config = get_config(review_id)
    snapshot = review_graph.get_state(config)

    if not snapshot.values:
        raise ValueError("Review not found.")

    if snapshot.next:
        raise ValueError("Review is still running.")

    state = snapshot.values

    if state.get("extraction_status") not in [
        "partially_completed",
        "failed"
    ]:
        raise ValueError("This review does not require extraction recovery.")

    if not state.get("full_text_eligible_papers"):
        raise ValueError("No eligible papers are available for extraction.")

    # Schedule the extraction node without rerunning previous stages.
    review_graph.update_state(
        config,
        {
            "extraction_status": "pending",
            "current_stage": "extraction_retry_queued"
        },
        as_node="full_text_eligibility"
    )


def continue_extraction_retry(review_id: str):
    config = get_config(review_id)

    # Continue from the checkpoint's scheduled extraction node.
    review_graph.invoke(None, config)

def continue_review(review_id: str):
    config = get_config(review_id)

    snapshot = review_graph.get_state(config)

    if not snapshot.values:
        raise ValueError("Review checkpoint not found.")

    if not snapshot.next:
        raise ValueError("There are no pending nodes to execute.")

    print(f"[Review Service] Resuming review at: {snapshot.next}")

    return review_graph.invoke(None, config)