import os
import json
import hashlib
import chromadb

from pathlib import Path
from sentence_transformers import SentenceTransformer


ROOT_DIR = Path(__file__).resolve().parent.parent

PROCESSED_DIR = str(ROOT_DIR / "data" / "processed")
CHROMA_DIR = str(ROOT_DIR / "data" / "chroma_db")

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

BATCH_SIZE = 5000


def split_text(text):
    """Split text into overlapping character chunks."""

    chunks = []
    start = 0

    while start < len(text):

        end = start + CHUNK_SIZE
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks


def build_index():

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(CHROMA_DIR, exist_ok=True)

    print("[RAG] Processed directory:", PROCESSED_DIR)
    print("[RAG] Database directory:", CHROMA_DIR)

    client = chromadb.PersistentClient(
        path=CHROMA_DIR
    )

    collection = client.get_or_create_collection(
        name="academic_papers",
        metadata={"hnsw:space": "cosine"}
    )

    documents = []
    metadatas = []
    ids = []

    print("\n[RAG] Processing extracted papers...")

    for filename in sorted(os.listdir(PROCESSED_DIR)):

        if not filename.endswith(".json") or filename == "screening_cache.json":
            continue

        filepath = os.path.join(PROCESSED_DIR, filename)

        with open(filepath, "r", encoding="utf-8") as file:
            paper_data = json.load(file)

        pages = paper_data.get("pages", [])

        if not pages:
            print(f"[RAG] Skipping {filename}: no extracted pages.")
            continue

        source_pdf = os.path.basename(
            paper_data.get("source_pdf") or filename.replace(".json", ".pdf")
        )

        for page in paper_data.get("pages", []):

            page_number = page["page_number"]
            text = page.get("text", "")

            if not text.strip():
                continue

            chunks = split_text(text)

            for chunk_index, chunk in enumerate(chunks):

                unique_id = hashlib.md5(
                    f"{source_pdf}_{page_number}_{chunk_index}".encode()
                ).hexdigest()

                documents.append(chunk)

                metadatas.append({
                    "source_pdf": source_pdf,
                    "page_number": page_number,
                    "chunk_index": chunk_index
                })

                ids.append(unique_id)

    if not documents:
        print("[RAG] No text chunks found.")
        return 0

    print(f"[RAG] Generated {len(documents)} chunks.")

    print("[RAG] Loading embedding model...")
    model = SentenceTransformer(MODEL_NAME)

    total_indexed = 0

    for start in range(0, len(documents), BATCH_SIZE):

        end = min(start + BATCH_SIZE, len(documents))

        batch_documents = documents[start:end]
        batch_metadatas = metadatas[start:end]
        batch_ids = ids[start:end]

        print(
            f"\n[RAG] Indexing batch "
            f"{start // BATCH_SIZE + 1}: "
            f"{len(batch_documents)} chunks"
        )

        embeddings = model.encode(
            batch_documents,
            show_progress_bar=True
        ).tolist()

        collection.upsert(
            ids=batch_ids,
            documents=batch_documents,
            metadatas=batch_metadatas,
            embeddings=embeddings
        )

        total_indexed += len(batch_documents)

        print(
            f"[RAG] Progress: {total_indexed}/{len(documents)}"
        )

    print("\n========== RAG INDEX SUMMARY ==========")
    print("Chunks processed:", len(documents))
    print("Chunks indexed:", total_indexed)
    print("Collection size:", collection.count())
    print("Database location:", CHROMA_DIR)

    return total_indexed


if __name__ == "__main__":
    build_index()
