from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class QdrantSettings:
    url: str = getenv("QDRANT_URL", "http://qdrant:6333")
    collection: str = getenv("QDRANT_COLLECTION", "deepface_embeddings")


qdrant_settings = QdrantSettings()
