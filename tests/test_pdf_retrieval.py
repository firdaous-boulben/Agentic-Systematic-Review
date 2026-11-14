
from tools.academic_search import search_openalex
from tools.pdf_retrieval import retrieve_pdfs


query = "explainable recommender systems in education"

# Retrieve academic papers
papers = search_openalex(query, max_results=10)

# Attempt to download available PDFs
papers = retrieve_pdfs(papers)

print("\n========== PDF RETRIEVAL RESULTS ==========")

for paper in papers:
    print("\nTitle:", paper["title"])
    print("Status:", paper["pdf_download_status"])
    print("PDF path:", paper["pdf_path"])
    print("Error:", paper["pdf_error"])
