import pytest

from app.ml.matcher import MatchCandidate, cosine_similarity, find_best_match


def test_cosine_similarity_returns_one_for_identical_vectors():
    score = cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0])

    assert score == 1.0


def test_cosine_similarity_returns_zero_for_orthogonal_vectors():
    score = cosine_similarity([1.0, 0.0], [0.0, 1.0])

    assert score == 0.0


def test_cosine_similarity_rejects_empty_vectors():
    with pytest.raises(ValueError, match="must not be empty"):
        cosine_similarity([], [1.0])


def test_cosine_similarity_rejects_mismatched_dimensions():
    with pytest.raises(ValueError, match="same dimensions"):
        cosine_similarity([1.0, 0.0], [1.0])


def test_cosine_similarity_rejects_zero_magnitude_vector():
    with pytest.raises(ValueError, match="zero magnitude"):
        cosine_similarity([0.0, 0.0], [1.0, 0.0])


def test_find_best_match_returns_matching_employee_above_threshold():
    result = find_best_match(
        query_vector=[1.0, 0.0],
        candidates=[
            MatchCandidate(employee_id=1, vector=[0.0, 1.0]),
            MatchCandidate(employee_id=2, vector=[1.0, 0.0]),
        ],
        threshold=0.85,
    )

    assert result.matched is True
    assert result.employee_id == 2
    assert result.score == 1.0


def test_find_best_match_denies_when_score_is_below_threshold():
    result = find_best_match(
        query_vector=[1.0, 0.0],
        candidates=[MatchCandidate(employee_id=1, vector=[0.7, 0.7])],
        threshold=0.9,
    )

    assert result.matched is False
    assert result.employee_id == 1
    assert result.score is not None
    assert result.score < 0.9


def test_find_best_match_denies_when_no_candidates_exist():
    result = find_best_match(query_vector=[1.0, 0.0], candidates=[])

    assert result.matched is False
    assert result.employee_id is None
    assert result.score is None
    assert result.message == "No face embeddings available for matching."


def test_find_best_match_rejects_invalid_threshold():
    with pytest.raises(ValueError, match="between 0 and 1"):
        find_best_match(
            query_vector=[1.0, 0.0],
            candidates=[MatchCandidate(employee_id=1, vector=[1.0, 0.0])],
            threshold=1.1,
        )
