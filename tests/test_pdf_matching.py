import os
import chromadb

from tools.pdf_retrieval import create_filename

# 1. List downloaded PDFs
print("\n========== DOWNLOADED PDF FILES ==========")

pdf_directory = "data/papers"

pdf_files = [
    filename
    for filename in os.listdir(pdf_directory)
    if filename.lower().endswith(".pdf")
]

for filename in pdf_files:
    print(filename)

# 2. List PDF filenames stored in ChromaDB
print("\n========== INDEXED PDF FILES ==========")

client = chromadb.PersistentClient(path="data/chroma_db")
collection = client.get_collection("academic_papers")

metadata = collection.get(include=["metadatas"])["metadatas"]

indexed_files = sorted(set(
    item["source_pdf"]
    for item in metadata
))

for filename in indexed_files:
    print(filename)

# 3. Compare paper titles with available PDFs
print("\n========== FILENAME MATCHING ==========")

for filename in pdf_files:
    print("Available:", filename)

print("\nUse the following test with your included papers:")
