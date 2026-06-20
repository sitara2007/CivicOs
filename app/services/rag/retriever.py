from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

from app.core.config import get_settings


class LazySentenceTransformer:
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model: SentenceTransformer | None = None

    def encode(self, text: str):
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)
        return self._model.encode(text)


settings = get_settings()
# same model used while storing
model = LazySentenceTransformer(settings.rag_embedding_model)


client = QdrantClient(
    path=settings.rag_qdrant_path
)


collection_name = settings.rag_collection_name


def retrieve(query, top_k=3):

    # convert question into vector
    query_vector = model.encode(
        query
    ).tolist()


    results = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=top_k
    )


    chunks = []

    for point in results.points:

        chunks.append(
            {
                "text": point.payload["text"],
                "score": point.score
            }
        )


    return chunks



if __name__=="__main__":


    question = (
        "Who is eligible for this scheme?"
    )


    answers = retrieve(question)


    for item in answers:

        print("\nSCORE:",
              item["score"])

        print(
            item["text"][:300]
        )
