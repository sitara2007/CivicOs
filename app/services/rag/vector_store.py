from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.services.rag.loader import load_pdf
from app.services.rag.chunker import chunk_text


class LazySentenceTransformer:
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model: SentenceTransformer | None = None

    def encode(self, text: list[str]):
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)
        return self._model.encode(text)


settings = get_settings()
model = LazySentenceTransformer(settings.rag_embedding_model)

if settings.qdrant_url.strip():
    client = QdrantClient(url=settings.qdrant_url)
else:
    client = QdrantClient(path=settings.rag_qdrant_path)

collection_name = settings.rag_collection_name


def create_collection():

    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "size":384,
                "distance":"Cosine"
            }
        )


def store_chunks(chunks):

    create_collection()

    embeddings = model.encode(chunks)

    points=[]

    for i, vector in enumerate(embeddings):

        points.append(
            PointStruct(
                id=i,
                vector=vector.tolist(),
                payload={
                    "text":chunks[i]
                }
            )
        )

    client.upsert(
        collection_name=collection_name,
        points=points
    )

if __name__ == "__main__":
    # Removed the local imports to avoid confusion
    text = load_pdf("data/documents/scheme.pdf")
    chunks = chunk_text(text)
    store_chunks(chunks)
    print("Stored:", len(chunks))
