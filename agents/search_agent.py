from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from config.llm import get_llm
from tools.academic_search import search_openalex

load_dotenv()

# Initialize LLM
llm = get_llm()

parser = JsonOutputParser()

# Search strategy prompt
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an academic literature search specialist.

Given a research topic and a list of keywords,
generate 3 to 5 distinct academic search queries.

Queries should cover different aspects of the topic
while remaining relevant to the research question.

Return valid JSON in this format:
{{
    "search_queries": [
        "query 1",
        "query 2",
        "query 3"
    ]
}}"""
    ),
    (
        "human",
        """Research topic: {topic}

Research question: {research_question}

Keywords: {keywords}"""
    )
])

search_chain = prompt | llm | parser


def generate_search_queries(state):

    print("\n[Search Agent] Generating academic search queries...")

    result = search_chain.invoke({
        "topic": state["topic"],
        "research_question": state["research_question"],
        "keywords": ", ".join(state["protocol"]["keywords"])
    })

    queries = result["search_queries"]

    print(f"[Search Agent] Generated {len(queries)} queries.")

    return queries


def deduplicate_papers(papers):

    unique_papers = {}
    seen_titles = set()

    for paper in papers:

        doi = (paper.get("doi") or "").strip().lower()
        openalex_id = paper.get("openalex_id")
        title = (paper.get("title") or "").strip().lower()

        if doi:
            key = doi
        elif openalex_id:
            key = openalex_id
        else:
            key = title

        if not key or key in unique_papers:
            continue

        # Additional title-based duplicate check
        if title and title in seen_titles:
            continue

        unique_papers[key] = paper

        if title:
            seen_titles.add(title)

    return list(unique_papers.values())


def run_search_agent(state):

    print("\n[Search Agent] Starting literature search...")

    queries = generate_search_queries(state)

    all_papers = []

    for query in queries:

        try:
            papers = search_openalex(
                query=query,
                max_results=10
            )

            all_papers.extend(papers)

        except Exception as error:
            print(f"[Search Agent] Query failed: {query}")
            print("Error:", error)

    unique_papers = deduplicate_papers(all_papers)

    print("\n[Search Agent] Search completed.")
    print("Total retrieved:", len(all_papers))
    print("Unique papers:", len(unique_papers))

    return {
        "search_queries": queries,
        "retrieved_papers": all_papers,
        "unique_papers": unique_papers,
        "current_stage": "search_completed",
        "execution_logs": state.get("execution_logs", []) + [
            f"Generated {len(queries)} academic search queries.",
            f"Retrieved {len(all_papers)} papers.",
            f"Found {len(unique_papers)} unique papers."
        ]
    }