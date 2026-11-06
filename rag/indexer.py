import os
import json
import hashlib
import chromadb

from sentence_transformers import SentenceTransformer


PROCESSED_DIR = "data/processed"
CHROMA_DIR = "data/chroma_db"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


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

    print("\n[RAG] Loading embedding model...")

    model = SentenceTransformer(MODEL_NAME)

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

        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(
            PROCESSED_DIR,
            filename
        )

        with open(filepath, "r", encoding="utf-8") as file:
            paper_data = json.load(file)

        source_pdf = os.path.basename(
            paper_data.get("source_pdf", filename)
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
    print("[RAG] Generating embeddings...")

    embeddings = model.encode(
        documents,
        show_progress_bar=True
    ).tolist()

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings
    )

    print("\n========== RAG INDEX SUMMARY ==========")
    print("New chunks processed:", len(documents))
    print("Collection size:", collection.count())
    print("Database location:", CHROMA_DIR)

    return len(documents)


if __name__ == "__main__":
    build_index()
