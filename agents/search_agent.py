
import re
import unicodedata

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from config.llm import get_llm
from tools.academic_search import (
    search_openalex,
    search_crossref,
    normalize_doi
)

from server.utils.logging import add_execution_logs

load_dotenv()

# Initialize LLM
llm = get_llm()

parser = JsonOutputParser()


# ---------------------------------------------------------------------
# Search strategy
# ---------------------------------------------------------------------

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an academic literature search specialist.

Given a research topic and a list of keywords,
generate 3 to 5 distinct academic search queries
compatible with academic literature databases.

Requirements:
- Use relevant terms and exact phrases in double quotes.
- You may use uppercase AND and OR operators.
- Do not use wildcards (* or ?).
- Do not include publication-date restrictions or database-specific
  syntax such as PubMed field tags.
- Keep queries concise and focused.
- Each query should explore a distinct aspect of the research topic.

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


# ---------------------------------------------------------------------
# Deduplication helpers
# ---------------------------------------------------------------------

def normalize_title(title):
    """Normalize titles for duplicate detection."""

    if not title:
        return ""

    title = unicodedata.normalize("NFKD", title)
    title = title.encode("ascii", "ignore").decode("ascii")
    title = title.lower()

    title = re.sub(r"[^a-z0-9\s]", " ", title)
    title = re.sub(r"\s+", " ", title)

    return title.strip()


def get_source_name(paper):
    """Return the source name for a paper."""

    source = paper.get("source")

    if source:
        return source

    sources = paper.get("sources", [])

    return sources[0] if sources else "Unknown"


def merge_paper_metadata(existing, incoming):
    """
    Merge duplicate records while preserving metadata from both sources.

    Existing non-empty values are retained. Missing values are filled
    from the incoming record.
    """

    merged = existing.copy()

    existing_source = get_source_name(existing)
    incoming_source = get_source_name(incoming)

    sources = list(existing.get("sources", []))

    if existing_source not in sources:
        sources.append(existing_source)

    incoming_sources = incoming.get("sources", [incoming_source])

    for source in incoming_sources:
        if source and source not in sources:
            sources.append(source)

    merged["sources"] = sources

    # Preserve the first source as the primary source for compatibility.
    merged["source"] = existing_source

    # Fill missing metadata without overwriting existing information.
    for key, value in incoming.items():

        if key in {"source", "sources", "citations"}:
            continue

        existing_value = merged.get(key)

        if existing_value in (None, "", [], {}):
            if value not in (None, "", [], {}):
                merged[key] = value

    # Keep citation counts identifiable by their source.
    citation_counts = merged.get("citation_counts", {})

    if existing.get("citations") is not None:
        citation_counts[existing_source] = existing["citations"]

    if incoming.get("citations") is not None:
        citation_counts[incoming_source] = incoming["citations"]

    if citation_counts:
        merged["citation_counts"] = citation_counts

    # Preserve the original citation count as the primary value.
    if existing.get("citations") is not None:
        merged["citations"] = existing["citations"]
    elif incoming.get("citations") is not None:
        merged["citations"] = incoming["citations"]

    # Recalculate abstract availability after merging.
    merged["has_abstract"] = bool(merged.get("abstract"))

    return merged


# ---------------------------------------------------------------------
# Cross-source deduplication
# ---------------------------------------------------------------------

def deduplicate_papers(papers):
    """
    Deduplicate records retrieved from multiple academic sources.

    Matching priority:
    1. DOI
    2. OpenAlex ID
    3. Normalized title, when DOI information does not conflict

    Duplicate records are merged rather than discarded.
    """

    unique_papers = []

    doi_index = {}
    openalex_index = {}
    title_index = {}

    for paper in papers:

        doi = normalize_doi(paper.get("doi"))
        doi = doi.lower() if doi else None

        openalex_id = paper.get("openalex_id")
        title = normalize_title(paper.get("title"))

        match_index = None

        # 1. Match by DOI
        if doi and doi in doi_index:
            match_index = doi_index[doi]

        # 2. Match by OpenAlex ID
        if match_index is None and openalex_id:
            if openalex_id in openalex_index:
                match_index = openalex_index[openalex_id]

        # 3. Match by title only if DOI values do not conflict
        if match_index is None and title and title in title_index:

            candidate_index = title_index[title]
            candidate = unique_papers[candidate_index]

            candidate_doi = normalize_doi(candidate.get("doi"))
            candidate_doi = (
                candidate_doi.lower()
                if candidate_doi else None
            )

            if not doi or not candidate_doi or doi == candidate_doi:
                match_index = candidate_index

        # New record
        if match_index is None:

            match_index = len(unique_papers)
            unique_papers.append(paper.copy())

        else:
            # Merge duplicate metadata
            unique_papers[match_index] = merge_paper_metadata(
                unique_papers[match_index],
                paper
            )

        # Update indexes using the merged record
        merged_paper = unique_papers[match_index]

        merged_doi = normalize_doi(merged_paper.get("doi"))
        merged_doi = merged_doi.lower() if merged_doi else None

        merged_openalex_id = merged_paper.get("openalex_id")
        merged_title = normalize_title(merged_paper.get("title"))

        if merged_doi:
            doi_index[merged_doi] = match_index

        if merged_openalex_id:
            openalex_index[merged_openalex_id] = match_index

        if merged_title:
            title_index[merged_title] = match_index

    return unique_papers


# ---------------------------------------------------------------------
# Multi-source retrieval
# ---------------------------------------------------------------------

def run_search_agent(state):

    print("\n[Search Agent] Starting literature search...")

    queries = generate_search_queries(state)

    all_papers = []

    source_counts = {
        "OpenAlex": 0,
        "Crossref": 0
    }

    search_errors = []

    for query in queries:

        print(f"\n[Search Agent] Processing query: {query}")

        # OpenAlex retrieval
        try:
            openalex_papers = search_openalex(
                query=query,
                max_results=10
            )

            all_papers.extend(openalex_papers)
            source_counts["OpenAlex"] += len(openalex_papers)

        except Exception as error:
            message = f"OpenAlex failed for query '{query}': {error}"

            print(f"[Search Agent] {message}")
            search_errors.append(message)

        # Crossref retrieval
        try:
            crossref_papers = search_crossref(
                query=query,
                max_results=10
            )

            all_papers.extend(crossref_papers)
            source_counts["Crossref"] += len(crossref_papers)

        except Exception as error:
            message = f"Crossref failed for query '{query}': {error}"

            print(f"[Search Agent] {message}")
            search_errors.append(message)

    # Deduplicate and merge records across sources
    unique_papers = deduplicate_papers(all_papers)

    print("\n[Search Agent] Search completed.")
    print("OpenAlex retrieved:", source_counts["OpenAlex"])
    print("Crossref retrieved:", source_counts["Crossref"])
    print("Total retrieved:", len(all_papers))
    print("Unique papers:", len(unique_papers))

    # Count unique records associated with each source
    unique_source_counts = {
        "OpenAlex": sum(
            "OpenAlex" in paper.get("sources", [])
            for paper in unique_papers
        ),
        "Crossref": sum(
            "Crossref" in paper.get("sources", [])
            for paper in unique_papers
        )
    }

    print("Unique OpenAlex-associated papers:", unique_source_counts["OpenAlex"])
    print("Unique Crossref-associated papers:", unique_source_counts["Crossref"])

    execution_messages = [
        f"Generated {len(queries)} academic search queries.",
        f"Retrieved {source_counts['OpenAlex']} records from OpenAlex.",
        f"Retrieved {source_counts['Crossref']} records from Crossref.",
        f"Retrieved {len(all_papers)} records in total.",
        f"Found {len(unique_papers)} unique papers after cross-source deduplication."
    ]

    if search_errors:
        execution_messages.append(
            f"{len(search_errors)} source retrieval errors occurred."
        )

    return {
        "search_queries": queries,
        "retrieved_papers": all_papers,
        "unique_papers": unique_papers,
        "current_stage": "search_completed",
        "execution_logs": add_execution_logs(
            state.get("execution_logs", []),
            execution_messages
        )
    }
