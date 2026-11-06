from agents.protocol_agent import generate_protocol
from agents.search_agent import run_search_agent
from agents.screening_agent import run_screening_agent

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

search_result = run_search_agent(state)
state.update(search_result)

screening_result = run_screening_agent(state, max_papers=5)

print("\n========== SCREENING RESULTS ==========")

for paper in screening_result["screening_results"]:
    print("\nTitle:", paper["title"])
    print("Decision:", paper["screening_decision"])
    print("Reason:", paper["screening_reason"])

print("\n========== SCREENING STATISTICS ==========")
print("Included:", len(screening_result["included_papers"]))
print("Excluded:", len(screening_result["excluded_papers"]))
print("Uncertain:", len(screening_result["uncertain_papers"]))