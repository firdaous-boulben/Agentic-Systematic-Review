from agents.protocol_agent import generate_protocol
from agents.search_agent import run_search_agent
from agents.screening_agent import run_screening_agent
from agents.extraction_agent import run_extraction_agent

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

print("\n========== SCREENING CANDIDATES ==========")

print("\nInclusion criteria:")
for criterion in state["inclusion_criteria"]:
    print("-", criterion)

print("\nFirst five papers:")

for paper in state["unique_papers"][:5]:
    print("\nTitle:", paper["title"])
    print("Abstract:", (paper.get("abstract") or "MISSING")[:500])

screening_result = run_screening_agent(state, max_papers=5)
state.update(screening_result)

# For this isolated test, use the AI-selected included papers.
extraction_result = run_extraction_agent(state)

print("\n========== EXTRACTION RESULTS ==========")

for paper in extraction_result["extracted_data"]:
    print("\nTitle:", paper["title"])

    for field, value in paper["extracted_information"].items():
        print(f"{field.replace('_', ' ').title()}: {value}")

print("\nTotal extracted:", len(extraction_result["extracted_data"]))