from langgraph.types import Command
from workflow.graph import review_graph

topic = "Artificial Intelligence for Cybersecurity Threat Detection"

initial_state = {
    "topic": topic,
    "execution_logs": []
}

config = {
    "configurable": {
        "thread_id": "review_001"
    }
}

# Start workflow
result = review_graph.invoke(initial_state, config=config)

# Display screening results
print("\n========== HUMAN REVIEW ==========")

for category in [
    "included_papers",
    "excluded_papers",
    "uncertain_papers"
]:
    print(f"\n{category.upper().replace('_', ' ')}:")

    for paper in result[category]:
        print("-", paper["title"])
        print("  Reason:", paper["screening_reason"])

# Request human approval
approval = input(
    "\nDo you approve these screening results? (yes/no): "
).strip().lower()

# Resume workflow
result = review_graph.invoke(
    Command(resume=approval),
    config=config
)

if result.get("human_approval"):
    print("\n========== EXTRACTION RESULTS ==========")

    for paper in result.get("extracted_data", []):
        print("\nTitle:", paper["title"])

        for field, value in paper["extracted_information"].items():
            print(f"{field.replace('_', ' ').title()}: {value}")

else:
    print("\nExtraction skipped: screening was not approved.")

if result.get("human_approval"):
    print("\n========== QUALITY APPRAISAL ==========")

    for paper in result.get("quality_results", []):
        print("\nTitle:", paper["title"])

        appraisal = paper["quality_appraisal"]

        print("Study type:", appraisal["study_type"])

        for dimension, assessment in appraisal["assessments"].items():
            print(f"{dimension}: {assessment['rating']}")
            print("Reason:", assessment["reason"])

        print("\nFull-text verification:")
        for item in appraisal["full_text_verification"]:
            print("-", item)

print("\n========== RESEARCH SYNTHESIS ==========")
print(result.get("synthesis", "No synthesis available."))

print("\n========== CRITIC FEEDBACK ==========")
print(result.get("critic_feedback", "No feedback available."))
print("\nValidation status:", result.get("validation_status"))

print("\n========== WORKFLOW STATUS ==========")
print("Human approval:", result["human_approval"])
print("Current stage:", result["current_stage"])

print("\n========== PRISMA STATISTICS ==========")
for key, value in result.get("prisma_data", {}).items():
    print(f"{key}: {value}")

print("\n========== PRISMA DIAGRAM ==========")
print(result.get("prisma_diagram_path"))

print("\n========== FINAL REPORT ==========")
print(result.get("final_report", "No report generated."))

print("\nExecution logs:")
for log in result["execution_logs"]:
    print("-", log)