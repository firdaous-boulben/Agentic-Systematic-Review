import chromadb
from sentence_transformers import SentenceTransformer


CHROMA_DIR = "data/chroma_db"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class PaperRetriever:

    def __init__(self):

        self.model = SentenceTransformer(MODEL_NAME)

        self.client = chromadb.PersistentClient(
            path=CHROMA_DIR
        )

        self.collection = self.client.get_collection(
            name="academic_papers"
        )

    def search(self, query, top_k=5, source_pdf=None):
        query_embedding = self.model.encode(
            query
        ).tolist()

        search_args = {
            "query_embeddings": [query_embedding],
            "n_results": min(top_k, self.collection.count())
        }

        if source_pdf:
            search_args["where"] = {
                "source_pdf": source_pdf
            }

        results = self.collection.query(**search_args)

        retrieved_passages = []

        for index in range(len(results["documents"][0])):

            metadata = results["metadatas"][0][index]

            retrieved_passages.append({
                "text": results["documents"][0][index],
                "source_pdf": metadata["source_pdf"],
                "page_number": metadata["page_number"],
                "chunk_index": metadata["chunk_index"],
                "distance": results["distances"][0][index]
            })

        return retrieved_passages