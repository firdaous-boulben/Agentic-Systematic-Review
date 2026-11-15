
import os
import re
import html
import requests

from dotenv import load_dotenv

load_dotenv()

OPENALEX_API_URL = "https://api.openalex.org/works"
CROSSREF_API_URL = "https://api.crossref.org/works"


# ---------------------------------------------------------------------
# Shared metadata helpers
# ---------------------------------------------------------------------

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


def clean_abstract(abstract):
    """Remove HTML tags and decode entities from an abstract."""

    if not abstract:
        return ""

    abstract = re.sub(r"<[^>]+>", " ", abstract)
    abstract = html.unescape(abstract)

    return re.sub(r"\s+", " ", abstract).strip()


def normalize_doi(doi):
    """Normalize DOI values to a consistent URL format."""

    if not doi:
        return None

    doi = str(doi).strip()

    doi = re.sub(
        r"^https?://(dx\.)?doi\.org/",
        "",
        doi,
        flags=re.IGNORECASE
    )

    return f"https://doi.org/{doi}" if doi else None


def get_crossref_year(item):
    """Extract publication year from Crossref date metadata."""

    date_fields = [
        "published-print",
        "published-online",
        "published",
        "issued",
        "created"
    ]

    for field in date_fields:
        date_info = item.get(field) or {}
        date_parts = date_info.get("date-parts") or []

        if date_parts and date_parts[0]:
            return date_parts[0][0]

    return None


def get_crossref_authors(item):
    """Normalize Crossref author metadata."""

    authors = []

    for author in item.get("author", []):
        given = author.get("given", "").strip()
        family = author.get("family", "").strip()

        name = " ".join(part for part in [given, family] if part)

        if name:
            authors.append(name)

    return authors


def get_crossref_pdf_url(item):
    """Extract a PDF URL when Crossref provides one."""

    for link in item.get("link", []):
        content_type = link.get("content-type", "").lower()

        if "pdf" in content_type:
            return link.get("URL")

    return None


# ---------------------------------------------------------------------
# Query preparation
# ---------------------------------------------------------------------

def prepare_openalex_query(query):
    """
    Convert database-specific date syntax into OpenAlex filters
    and prepare wildcard terms for standard OpenAlex search.
    """

    start_year = None
    end_year = None

    # Extract PubMed-style date range: (2015:2026[dp])
    date_match = re.search(
        r"\(?\s*(\d{4})\s*:\s*(\d{4})\s*\[dp\]\s*\)?",
        query,
        flags=re.IGNORECASE
    )

    if date_match:
        start_year = int(date_match.group(1))
        end_year = int(date_match.group(2))

        # Remove the date expression and its preceding AND
        query = re.sub(
            r"\s+AND\s+\(?\s*\d{4}\s*:\s*\d{4}\s*\[dp\]\s*\)?",
            "",
            query,
            flags=re.IGNORECASE
        )

    # Remove any remaining trailing Boolean operator
    query = re.sub(
        r"\s+(AND|OR)\s*$",
        "",
        query,
        flags=re.IGNORECASE
    ).strip()

    # Remove trailing wildcards for standard stemmed search
    query = re.sub(
        r"\b([a-zA-Z]{3,})\*",
        r"\1",
        query
    )

    filters = []

    if start_year and end_year:
        filters.append(
            f"from_publication_date:{start_year}-01-01"
        )
        filters.append(
            f"to_publication_date:{end_year}-12-31"
        )

    return query, ",".join(filters) if filters else None


def prepare_crossref_filters(date_filter):
    """Convert the shared date range into Crossref filter syntax."""

    if not date_filter:
        return None

    filters = []

    for part in date_filter.split(","):
        if part.startswith("from_publication_date:"):
            date_value = part.split(":", 1)[1]
            filters.append(f"from-pub-date:{date_value}")

        elif part.startswith("to_publication_date:"):
            date_value = part.split(":", 1)[1]
            filters.append(f"until-pub-date:{date_value}")

    return ",".join(filters) if filters else None


# ---------------------------------------------------------------------
# OpenAlex normalization and retrieval
# ---------------------------------------------------------------------

def normalize_openalex_work(paper):
    """Normalize an OpenAlex work to the shared paper structure."""

    authors = [
        author.get("author", {}).get("display_name", "")
        for author in paper.get("authorships", [])
    ]

    location = paper.get("primary_location") or {}
    oa_location = paper.get("best_oa_location") or location
    source = location.get("source") or {}
    open_access = paper.get("open_access") or {}

    abstract = reconstruct_abstract(
        paper.get("abstract_inverted_index")
    )

    return {
        "openalex_id": paper.get("id"),
        "crossref_id": None,
        "doi": normalize_doi(paper.get("doi")),
        "title": paper.get("display_name"),
        "authors": authors,
        "year": paper.get("publication_year"),
        "abstract": abstract,
        "journal": source.get("display_name"),
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
        "sources": ["OpenAlex"],
        "has_abstract": bool(abstract),
        "is_open_access": open_access.get("is_oa", False),
        "oa_status": open_access.get("oa_status")
    }


def search_openalex(query, max_results=10):
    """Retrieve and normalize papers from OpenAlex."""

    api_key = os.getenv("OPENALEX_API_KEY")

    if not api_key:
        raise ValueError("OPENALEX_API_KEY is missing from .env")

    clean_query, date_filter = prepare_openalex_query(query)

    params = {
        "search": clean_query,
        "per_page": max_results,
        "sort": "relevance_score:desc",
        "select": (
            "id,doi,display_name,publication_year,"
            "authorships,abstract_inverted_index,"
            "primary_location,best_oa_location,"
            "cited_by_count,type,open_access,biblio"
        )
    }

    if date_filter:
        params["filter"] = date_filter

    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    print(f"\n[OpenAlex] Searching for: {clean_query}")

    if date_filter:
        print(f"[OpenAlex] Date filter: {date_filter}")

    try:
        response = requests.get(
            OPENALEX_API_URL,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

    except requests.RequestException as error:
        raise RuntimeError(
            f"OpenAlex retrieval failed: {error}"
        ) from error

    results = response.json().get("results", [])

    papers = [
        normalize_openalex_work(paper)
        for paper in results
    ]

    print(f"[OpenAlex] Retrieved {len(papers)} papers.")

    return papers


# ---------------------------------------------------------------------
# Crossref normalization and retrieval
# ---------------------------------------------------------------------

def normalize_crossref_work(item):
    """Normalize a Crossref work to the shared paper structure."""

    doi = normalize_doi(item.get("DOI"))

    titles = item.get("title") or []
    title = titles[0] if titles else None

    abstracts = clean_abstract(item.get("abstract"))
    pdf_url = get_crossref_pdf_url(item)

    licenses = item.get("license") or []
    license_url = (
        licenses[0].get("URL")
        if licenses else None
    )

    return {
        "openalex_id": None,
        "crossref_id": item.get("DOI"),
        "doi": doi,
        "title": title,
        "authors": get_crossref_authors(item),
        "year": get_crossref_year(item),
        "abstract": abstracts,
        "journal": (
            (item.get("container-title") or [None])[0]
        ),
        "url": doi or item.get("URL"),
        "landing_page_url": doi or item.get("URL"),
        "pdf_url": pdf_url,
        "oa_url": None,
        "license": license_url,
        "citations": item.get("is-referenced-by-count"),
        "type": item.get("type"),
        "source": "Crossref",
        "sources": ["Crossref"],
        "has_abstract": bool(abstracts),
        "is_open_access": None,
        "oa_status": None
    }


def search_crossref(query, max_results=10):
    """
    Retrieve and normalize papers from Crossref.

    CROSSREF_MAILTO is optional but recommended by Crossref
    for identifying your application.
    """

    clean_query, date_filter = prepare_openalex_query(query)

    params = {
        "query": clean_query,
        "rows": max_results,
        "select": (
            "DOI,title,author,published,published-print,"
            "published-online,issued,created,container-title,"
            "URL,type,is-referenced-by-count,abstract,"
            "link,license"
        )
    }

    crossref_date_filter = prepare_crossref_filters(date_filter)

    if crossref_date_filter:
        params["filter"] = crossref_date_filter

    mailto = os.getenv("CROSSREF_MAILTO")

    if mailto:
        params["mailto"] = mailto

    headers = {
        "User-Agent": (
            "ReviewAI/1.0 "
            "(Academic literature retrieval; "
            f"mailto:{mailto or 'not-provided'})"
        )
    }

    print(f"\n[Crossref] Searching for: {clean_query}")

    if crossref_date_filter:
        print(f"[Crossref] Date filter: {crossref_date_filter}")

    try:
        response = requests.get(
            CROSSREF_API_URL,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

    except requests.RequestException as error:
        raise RuntimeError(
            f"Crossref retrieval failed: {error}"
        ) from error

    results = (
        response.json()
        .get("message", {})
        .get("items", [])
    )

    papers = [
        normalize_crossref_work(item)
        for item in results
    ]

    print(f"[Crossref] Retrieved {len(papers)} papers.")

    return papers
