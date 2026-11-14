from tools.academic_search import search_openalex

query = "explainable recommender systems in education"

papers = search_openalex(query, max_results=10)

print("\n========== SEARCH RESULTS ==========")

for index, paper in enumerate(papers, start=1):

    print(f"\n--- Paper {index} ---")
    print("Title:", paper["title"])
    print("Authors:", ", ".join(paper["authors"]))
    print("Year:", paper["year"])
    print("DOI:", paper["doi"])
    print("Journal:", paper["journal"])
    print("Abstract:", paper["abstract"][:400])
    print("URL:", paper["url"])
    print("Citations:", paper["citations"])
    print("Open access:", paper["is_open_access"])
    print("OA status:", paper["oa_status"])
    print("PDF URL:", paper["pdf_url"])
    print("Landing page:", paper["landing_page_url"])
    print("License:", paper["license"])