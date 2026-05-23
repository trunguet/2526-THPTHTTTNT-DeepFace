from dataclasses import dataclass


@dataclass(frozen=True)
class ReindexReadiness:
    ready: bool
    reason: str


def check_reindex_readiness() -> ReindexReadiness:
    return ReindexReadiness(
        ready=False,
        reason=(
            "face_embeddings now stores source_image_key for future reindexing, "
            "but the automated reindex job is not implemented yet."
        ),
    )


def reindex_face_embeddings() -> None:
    readiness = check_reindex_readiness()
    if not readiness.ready:
        raise NotImplementedError(readiness.reason)
