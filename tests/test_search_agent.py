from agents.protocol_agent import generate_protocol
from agents.search_agent import run_search_agent

topic = "Explainable Recommender Systems in Education"

# Generate protocol
protocol = generate_protocol(topic)

# Prepare initial state
state = {
    "topic": topic,
    "research_question": protocol["research_question"],
    "protocol": protocol,
    "execution_logs": []
}

# Execute Search Agent
result = run_search_agent(state)

# Display search queries
print("\n========== SEARCH QUERIES ==========")

for query in result["search_queries"]:
    print("-", query)

# Display statistics
print("\n========== SEARCH STATISTICS ==========")

print("Retrieved papers:", len(result["retrieved_papers"]))
print("Unique papers:", len(result["unique_papers"]))

# Display first five papers
print("\n========== RETRIEVED PAPERS ==========")

for index, paper in enumerate(result["unique_papers"][:5], 1):

    print(f"\nPaper {index}:")
    print("Title:", paper["title"])
    print("Year:", paper["year"])
    print("DOI:", paper["doi"])
    print("Source:", paper["source"])