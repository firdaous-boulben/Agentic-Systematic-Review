from agents.protocol_agent import generate_protocol
from agents.search_agent import run_search_agent
from agents.screening_agent import run_screening_agent
from agents.extraction_agent import run_extraction_agent
from agents.appraisal_agent import run_appraisal_agent
from agents.synthesis_agent import run_synthesis_agent

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
state.update(run_appraisal_agent(state))

synthesis_result = run_synthesis_agent(state)

print("\n========== RESEARCH SYNTHESIS ==========")
print(synthesis_result["synthesis"])

print("\n========== EXECUTION STATUS ==========")
print("Stage:", synthesis_result["current_stage"])

for log in synthesis_result["execution_logs"]:
    print("-", log)