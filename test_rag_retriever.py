from rag.retriever import PaperRetriever

retriever = PaperRetriever()

query = "How are explainable recommender systems evaluated in education?"

results = retriever.search(query, top_k=5)

print("\n========== RAG RETRIEVAL RESULTS ==========")

for index, result in enumerate(results, start=1):

    print(f"\n--- Result {index} ---")
    print("Source:", result["source_pdf"])
    print("Page:", result["page_number"])
    print("Distance:", round(result["distance"], 4))
    print("Text:")
    print(result["text"][:700])
