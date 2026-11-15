
import os
import re
import html
import requests
import pymupdf
import time
    
from urllib.parse import urlparse, quote
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

def extract_abstract_from_pdf_url(pdf_url):
    """
    Recover an abstract directly from a PDF.

    Uses Python only.
    Returns an empty string if extraction fails.
    """

    if not pdf_url or urlparse(pdf_url).scheme not in ("http", "https"):
        return ""

    try:
        # Download PDF with a 20 MB safety limit.
        content = bytearray()

        with requests.get(
            pdf_url,
            timeout=(10, 45),
            stream=True
        ) as response:

            response.raise_for_status()

            for chunk in response.iter_content(chunk_size=65536):
                content.extend(chunk)

                if len(content) > 20 * 1024 * 1024:
                    return ""

        if not content.startswith(b"%PDF"):
            return ""

        # Read the first five pages.
        with pymupdf.open(
            stream=bytes(content),
            filetype="pdf"
        ) as document:

            text = "\n".join(
                document[i].get_text("text")
                for i in range(min(5, len(document)))
            )

        # Identify the abstract section.
        match = re.search(
            r"\bABSTRACT\s*:?\s*(.*?)\s*"
            r"(?:RECOMMENDED\s+CITATION\s*:|"
            r"KEYWORDS\s*:|"
            r"JEL\s+(?:CLASSIFICATION|CODES)\s*:|"
            r"1[.\s]+INTRODUCTION\b)",
            text,
            flags=re.IGNORECASE | re.DOTALL
        )

        if not match:
            return ""

        abstract = re.sub(
            r"\s+",
            " ",
            match.group(1)
        ).strip()

        # Reject suspicious extraction results.
        if not 80 <= len(abstract) <= 3000:
            return ""

        return abstract

    except Exception as error:
        print(
            "[Metadata] PDF abstract extraction failed:",
            type(error).__name__
        )

        return ""

def enrich_missing_abstracts(papers):
    """
    Recover missing abstracts from OpenAlex.
    Preserve the original DOI and existing paper structure.
    """

    api_key = os.getenv("OPENALEX_API_KEY")

    headers = (
        {"Authorization": f"Bearer {api_key}"}
        if api_key else {}
    )

    recovered = 0

    for paper in papers:

        if (paper.get("abstract") or "").strip():
            continue

        original_doi = normalize_doi(paper.get("doi"))

        if not original_doi:
            continue

        doi = original_doi.split("doi.org/", 1)[-1]

        candidates = [doi]

        # IMF publications may have a related publication DOI.
        # Do not apply this rule to unrelated publishers.
        if (
            doi.lower().startswith("10.5089/")
            and re.search(r"\.a\d{3}$", doi, re.IGNORECASE)
        ):
            parent_doi = re.sub(
                r"\.a\d{3}$",
                "",
                doi,
                flags=re.IGNORECASE
            )
            candidates.append(parent_doi)

        for candidate in candidates:

            try:
                response = requests.get(
                    f"{OPENALEX_API_URL}/https://doi.org/{candidate}",
                    headers=headers,
                    timeout=20
                )

                if response.status_code == 404:
                    continue

                if response.status_code in (401, 403, 429):
                    print(
                        "[Metadata] OpenAlex access or rate limit "
                        f"error: {response.status_code}"
                    )
                    return papers

                response.raise_for_status()
                work = response.json()

            except (requests.RequestException, ValueError) as error:
                print(
                    f"[Metadata] Lookup failed: {candidate}: "
                    f"{type(error).__name__}"
                )
                continue

            returned_doi = normalize_doi(work.get("doi"))
            expected_doi = normalize_doi(candidate)

            if (
                not returned_doi
                or returned_doi.lower() != expected_doi.lower()
            ):
                continue

            abstract = reconstruct_abstract(
                work.get("abstract_inverted_index")
            )
            
            # Discover additional PDF locations for the exact DOI.
            # Never borrow PDF links from related but different DOIs.
            if candidate.lower() == doi.lower() and not paper.get("pdf_url"):

                locations = [
                    work.get("best_oa_location"),
                    *(work.get("locations") or []),
                    work.get("primary_location"),
                ]

                for location in locations:

                    if not isinstance(location, dict):
                        continue

                    if location.get("is_oa") is False:
                        continue

                    discovered_url = location.get("pdf_url")

                    if (
                        discovered_url
                        and discovered_url.startswith(("https://", "http://"))
                    ):
                        paper["pdf_url"] = discovered_url
                        paper["pdf_discovery_source"] = "OpenAlex"

                        print(
                            "[Metadata] PDF URL discovered:",
                            paper.get("title")
                        )
                        break


            if not abstract:
                continue

            is_related_doi = candidate.lower() != doi.lower()

            if is_related_doi:
                # Check title overlap before linking two DOI records.
                original_words = set(re.findall(
                    r"[a-z]{4,}",
                    (paper.get("title") or "").lower()
                ))

                related_words = set(re.findall(
                    r"[a-z]{4,}",
                    (work.get("display_name") or "").lower()
                ))

                common = original_words & related_words

                if (
                    len(common) < 2
                    or len(common) / max(
                        1, min(len(original_words), len(related_words))
                    ) < 0.25
                ):
                    continue

                paper["original_title"] = paper.get("title")

                paper["title"] = (
                    work.get("display_name") or paper.get("title")
                )

                paper["year"] = (
                    work.get("publication_year") or paper.get("year")
                )

            elif paper.get("year") is None:
                paper["year"] = work.get("publication_year")

            paper["abstract"] = abstract
            paper["has_abstract"] = True

            # Preserve the original DOI and source.
            paper["abstract_source"] = "OpenAlex"
            paper["abstract_source_doi"] = returned_doi

            recovered += 1

            print(
                f"[Metadata] Abstract recovered: "
                f"{paper.get('title')}"
            )

            break

    # Fallback: Recover abstracts from available PDFs
    for paper in papers:

        # Skip papers that already have an abstract.
        if (paper.get("abstract") or "").strip():
            continue

        pdf_url = paper.get("pdf_url")

        if not pdf_url:
            continue
        
        # A component or book chapter may link to a larger
        # publication PDF rather than its own full text.
        # Do not automatically assign that publication's abstract.
        if (
            paper.get("type") in {"component", "book-chapter"}
            and paper.get("pdf_discovery_source") == "OpenAlex"
        ):
            print(
                "[Metadata] PDF requires identity verification:",
                paper.get("title")
            )
            continue

        print(
            "[Metadata] Trying PDF abstract recovery:",
            paper.get("title")
        )

        abstract = extract_abstract_from_pdf_url(pdf_url)

        if not abstract:
            continue

        paper["abstract"] = abstract
        paper["has_abstract"] = True

        # Keep evidence of where the abstract came from.
        paper["abstract_source"] = "publisher_pdf"
        paper["abstract_source_url"] = pdf_url

        recovered += 1

        print(
            "[Metadata] Abstract recovered from PDF:",
            paper.get("title")
        )
        
    # FINAL FALLBACK: SEMANTIC SCHOLAR
    semantic_recovered = 0

    for paper in papers:

        # Skip papers that already have abstracts
        if (paper.get("abstract") or "").strip():
            continue

        original_doi = normalize_doi(paper.get("doi"))

        if not original_doi:
            continue

        doi = original_doi.split("doi.org/", 1)[-1]

        url = (
            "https://api.semanticscholar.org/graph/v1/paper/"
            + "DOI:"
            + quote(doi, safe="")
        )

        try:
            response = requests.get(
                url,
                params={
                    "fields": (
                        "title,year,abstract,"
                        "externalIds,openAccessPdf"
                    )
                },
                timeout=15
            )

            if response.status_code == 429:
                print("[Metadata] Semantic Scholar rate limit reached.")
                break

            if response.status_code != 200:
                continue

            data = response.json()

            # Automatic identity check: exact DOI match
            returned_doi = (
                data.get("externalIds") or {}
            ).get("DOI")

            if not returned_doi:
                continue

            if (
                normalize_doi(returned_doi).lower()
                != original_doi.lower()
            ):
                continue

            # First try the API abstract
            abstract = clean_abstract(data.get("abstract"))

            source = "SemanticScholar"

            # If unavailable, try its open-access PDF
            if not abstract:

                pdf_data = data.get("openAccessPdf") or {}
                pdf_url = pdf_data.get("url")

                if pdf_url:
                    abstract = extract_abstract_from_pdf_url(
                        pdf_url
                    )

                    if abstract:
                        source = "SemanticScholar_PDF"

                        if not paper.get("pdf_url"):
                            paper["pdf_url"] = pdf_url

            if not abstract:
                continue

            # Update the existing paper
            paper["abstract"] = abstract
            paper["has_abstract"] = True
            paper["abstract_source"] = source
            paper["abstract_source_doi"] = original_doi

            if paper.get("year") is None:
                paper["year"] = data.get("year")

            recovered += 1
            semantic_recovered += 1

            print(
                "[Metadata] Abstract recovered:",
                paper.get("title")
            )

            # Small delay to reduce API throttling
            time.sleep(1)

        except (requests.RequestException, ValueError) as error:
            print(
                "[Metadata] Semantic Scholar lookup failed:",
                type(error).__name__
            )
            continue

    print(f"[Metadata] Total abstracts recovered: {recovered}")

    return papers