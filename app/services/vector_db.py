from qdrant_client import QdrantClient
from pydantic_settings import BaseSettings
from loguru import logger

class QdrantConfig(BaseSettings):
    url: str = "http://localhost:6333"
    api_key: str = ""

class VectorDatabase:
    def __init__(self, config: QdrantConfig):
        self.client = QdrantClient(url=config.url, api_key=config.api_key)
        logger.info("Qdrant client initialized")

    def search(self, collection_name: str, query_vector: list, limit: int = 5):
        try:
            return self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit
            )
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

# Use dependency injection for your FastAPI app later