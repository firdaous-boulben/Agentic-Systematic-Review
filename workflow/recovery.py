from workflow.graph import review_graph
from langgraph.types import Command


def get_workflow_status(config):
    snapshot = review_graph.get_state(config)

    if not snapshot.values:
        return {
            "status": "not_found",
            "current_stage": None,
            "failed_stage": None,
            "next_steps": []
        }

    failed_tasks = [
        task for task in snapshot.tasks
        if task.error is not None
    ]

    if failed_tasks:
        status = "failed"
        failed_stage = failed_tasks[0].name
    elif snapshot.next:
        status = "interrupted"
        failed_stage = None
    else:
        status = "completed"
        failed_stage = None

    return {
        "status": status,
        "current_stage": snapshot.values.get("current_stage"),
        "failed_stage": failed_stage,
        "next_steps": list(snapshot.next),
        "topic": snapshot.values.get("topic"),
        "state": snapshot.values
    }


def resume_workflow(config):
    status = get_workflow_status(config)

    if status["status"] == "not_found":
        raise ValueError("Review not found.")

    if status["status"] == "completed":
        raise ValueError("This review has already completed.")

    if not status["next_steps"]:
        raise ValueError("No pending workflow steps to resume.")

    return review_graph.invoke(None, config=config)


def retry_failed_stage(config):
    status = get_workflow_status(config)

    if status["status"] != "failed":
        raise ValueError("There is no failed stage to retry.")

    failed_stage = status["failed_stage"]

    print(f"\nRetrying failed stage: {failed_stage}")

    return review_graph.invoke(None, config=config)


def resume_human_review(config, decision):
    status = get_workflow_status(config)

    if "human_review" not in status["next_steps"]:
        raise ValueError("The review is not waiting for human approval.")

    return review_graph.invoke(
        Command(resume=decision),
        config=config
    )
