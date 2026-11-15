
import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path


# Resolve the database path relative to the project root.
ROOT_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = str(ROOT_DIR / "data" / "chroma_db")

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class PaperRetriever:

    def __init__(self):

        print("[RAG] Loading embedding model...")

        self.model = SentenceTransformer(MODEL_NAME)

        self.client = chromadb.PersistentClient(
            path=CHROMA_DIR
        )

        self.collection = self.client.get_collection(
            name="academic_papers"
        )

        print(
            f"[RAG] Connected to collection: "
            f"{self.collection.name}"
        )
        print(
            f"[RAG] Indexed chunks: "
            f"{self.collection.count()}"
        )

    def search(self, query, top_k=5, source_pdf=None):

        collection_count = self.collection.count()

        if collection_count == 0:
            print("[RAG] The collection is empty.")
            return []

        if top_k <= 0:
            return []

        query_embedding = self.model.encode(
            query
        ).tolist()

        search_args = {
            "query_embeddings": [query_embedding],
            "n_results": min(top_k, collection_count)
        }

        if source_pdf:
            search_args["where"] = {
                "source_pdf": source_pdf
            }

        results = self.collection.query(**search_args)

        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        if not documents:
            print(
                f"[RAG] No passages found for: {source_pdf}"
            )
            return []

        retrieved_passages = []

        for document, metadata, distance in zip(
            documents, metadatas, distances
        ):

            if not document:
                continue

            metadata = metadata or {}

            retrieved_passages.append({
                "text": document,
                "source_pdf": metadata.get("source_pdf"),
                "page_number": metadata.get("page_number"),
                "chunk_index": metadata.get("chunk_index"),
                "distance": distance
            })

        print(
            f"[RAG] Retrieved {len(retrieved_passages)} "
            f"passages for: {source_pdf or 'all papers'}"
        )

        return retrieved_passages
