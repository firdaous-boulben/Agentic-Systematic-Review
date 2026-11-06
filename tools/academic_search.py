
import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENALEX_API_URL = "https://api.openalex.org/works"


def reconstruct_abstract(inverted_index):
    """Reconstruct an abstract from OpenAlex inverted index."""

    if not inverted_index:
        return ""

    words = {}

    for word, positions in inverted_index.items():
        for position in positions:
            words[position] = word

    return " ".join(
        words[position] for position in sorted(words)
    )


def search_openalex(query, max_results=10):

    api_key = os.getenv("OPENALEX_API_KEY")

    if not api_key:
        raise ValueError("OPENALEX_API_KEY is missing from .env")

    params = {
        "search": query,
        "per_page": max_results,
        "sort": "relevance_score:desc",
        "api_key": api_key,
        "select": (
            "id,doi,display_name,publication_year,"
            "authorships,abstract_inverted_index,"
            "primary_location,best_oa_location,"
            "cited_by_count,type,open_access,biblio"
        )
    }

    print(f"\n[OpenAlex] Searching for: {query}")

    response = requests.get(
        OPENALEX_API_URL,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    results = response.json().get("results", [])

    papers = []

    for paper in results:

        authors = [
            author.get("author", {}).get("display_name", "")
            for author in paper.get("authorships", [])
        ]

        location = paper.get("primary_location") or {}
        oa_location = paper.get("best_oa_location") or location
        source = location.get("source") or {}
        open_access = paper.get("open_access") or {}

        papers.append({
            "openalex_id": paper.get("id"),
            "doi": paper.get("doi"),
            "title": paper.get("display_name"),
            "authors": authors,
            "year": paper.get("publication_year"),
            "abstract": reconstruct_abstract(
                paper.get("abstract_inverted_index")
            ),
            "journal": source.get("display_name"),

            # Publication and full-text locations
            "url": location.get("landing_page_url"),
            "landing_page_url": (
                oa_location.get("landing_page_url")
                or location.get("landing_page_url")
            ),
            "pdf_url": oa_location.get("pdf_url"),
            "oa_url": open_access.get("oa_url"),
            "license": oa_location.get("license"),

            "citations": paper.get("cited_by_count"),
            "type": paper.get("type"),
            "source": "OpenAlex",
            "has_abstract": bool(
                paper.get("abstract_inverted_index")
            ),
            "is_open_access": open_access.get("is_oa", False),
            "oa_status": open_access.get("oa_status")
        })

    print(f"[OpenAlex] Retrieved {len(papers)} papers.")

    return papers
