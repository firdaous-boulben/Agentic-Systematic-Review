
from langgraph.types import Command
from workflow.graph import review_graph


def print_review_status(state):
    print("\n========== REVIEW STATUS ==========")
    print("Topic:", state.get("topic", "Unknown"))
    print("Current stage:", state.get("current_stage", "Unknown"))
    print("Retrieved papers:", len(state.get("unique_papers", [])))
    print("Screening results:", len(state.get("screening_results", [])))
    print("Full-text eligible:", len(state.get("full_text_eligible_papers", [])))
    print("Extracted papers:", len(state.get("extracted_data", [])))

    if state.get("final_report"):
        print("Final report:", state["final_report"])

    print("===================================\n")


# Select the review to open
thread_id = input("Review ID [review_001]: ").strip() or "review_001"

config = {
    "configurable": {
        "thread_id": thread_id
    }
}

# Check whether this review already exists
snapshot = review_graph.get_state(config)

if not snapshot.values:
    # Start a new review
    print("\nStarting a new review.")

    topic = input("Enter research topic: ").strip()

    if not topic:
        print("Topic cannot be empty.")
        raise SystemExit

    initial_state = {
        "topic": topic,
        "execution_logs": []
    }

    result = review_graph.invoke(initial_state, config=config)

else:
    # Existing review
    print("\nExisting review found.")
    print_review_status(snapshot.values)

    if not snapshot.next:
        print("This review has already completed.")
        print("Use a different Review ID to start another review.")
        raise SystemExit

    # Resume a pending human approval
    if "human_review" in snapshot.next:
        print("This review is waiting for human approval.")

        approval = input(
            "Approve screening? (yes/no): "
        ).strip().lower()

        result = review_graph.invoke(
            Command(resume=approval),
            config=config
        )

    else:
        # Resume from the last saved checkpoint
        print("Resuming interrupted workflow...")
        
        result = review_graph.invoke(
            None,
            config=config
        )


# Check whether human approval is now required
snapshot = review_graph.get_state(config)

if "human_review" in snapshot.next:
    state = snapshot.values

    print("\nScreening summary:")
    print("Included:", len(state.get("included_papers", [])))
    print("Excluded:", len(state.get("excluded_papers", [])))
    print("Uncertain:", len(state.get("uncertain_papers", [])))

    approval = input(
        "\nApprove screening? (yes/no): "
    ).strip().lower()

    result = review_graph.invoke(
        Command(resume=approval),
        config=config
    )


# Display latest saved state
snapshot = review_graph.get_state(config)
print_review_status(snapshot.values)

if snapshot.next:
    print("Workflow still has pending steps:", snapshot.next)
else:
    print("Workflow execution completed.")
