from agents.protocol_agent import generate_protocol
from agents.search_agent import run_search_agent
from agents.screening_agent import run_screening_agent
from agents.extraction_agent import run_extraction_agent
from agents.appraisal_agent import run_appraisal_agent

topic = "Explainable Recommender Systems in Education"

protocol = generate_protocol(topic)

state = {
    "topic": topic,
    "research_question": protocol["research_question"],
    "protocol": protocol,
    "inclusion_criteria": protocol["inclusion_criteria"],
    "exclusion_criteria": protocol["exclusion_criteria"],
    "execution_logs": []
}

state.update(run_search_agent(state))
state.update(run_screening_agent(state, max_papers=5))
state.update(run_extraction_agent(state))

appraisal_result = run_appraisal_agent(state)

print("\n========== QUALITY APPRAISAL RESULTS ==========")

for paper in appraisal_result["quality_results"]:
    print("\nTitle:", paper["title"])

    appraisal = paper["quality_appraisal"]

    print("Study type:", appraisal["study_type"])

    for dimension, assessment in appraisal["assessments"].items():
        print(f"\n{dimension}: {assessment['rating']}")
        print("Reason:", assessment["reason"])

    print("\nFull-text verification:")
    for item in appraisal["full_text_verification"]:
        print("-", item)

print("\nTotal assessed:", len(appraisal_result["quality_results"]))