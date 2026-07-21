import logging

from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

class SafeReranker:
    def __init__(self, model_name: str = "cross-encoder/bge-reranker-large"):
        self._model_name = model_name
        self._model = None

    def score(self, pairs):
        if not self._model:
            try:
                self._model = CrossEncoder(self._model_name)
            except Exception as e:
                logger.warning(f"Could not load Hugging Face model {self._model_name}: {e}. Falling back to default scoring.")  # noqa: E501
                return [0.0] * len(pairs)

        return self._model.score(pairs)
