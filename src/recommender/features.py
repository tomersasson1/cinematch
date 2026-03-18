from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer

from . import config


@dataclass
class ContentFeatures:
    """
    Container for content-based movie features.

    Attributes
    ----------
    movies:
        Movies DataFrame aligned with feature_matrix rows.
    feature_matrix:
        2D numpy array of shape (n_movies, n_features).
    feature_names:
        Names of the features (e.g. genres).
    item_id_to_row:
        Mapping from movieId to row index in feature_matrix.
    """

    movies: pd.DataFrame
    feature_matrix: np.ndarray
    feature_names: List[str]
    item_id_to_row: Dict[int, int]


def _split_genres(genres_str: str) -> List[str]:
    if pd.isna(genres_str) or genres_str == "(no genres listed)":
        return []
    return [g.strip() for g in str(genres_str).split("|") if g and g != "(no genres listed)"]


def build_genre_features(movies: pd.DataFrame) -> ContentFeatures:
    """
    Build multi-hot genre features for each movie.
    """
    movies = movies.copy()
    movies["genre_list"] = movies[config.GENRES_COL].apply(_split_genres)

    mlb = MultiLabelBinarizer()
    genre_matrix = mlb.fit_transform(movies["genre_list"])
    feature_names = list(mlb.classes_)

    item_id_to_row = {
        int(movie_id): idx for idx, movie_id in enumerate(movies[config.ITEM_ID_COL].tolist())
    }

    return ContentFeatures(
        movies=movies,
        feature_matrix=genre_matrix.astype(np.float32),
        feature_names=feature_names,
        item_id_to_row=item_id_to_row,
    )


def build_user_preference_vector(
    preferred_genres: Sequence[str],
    liked_movie_ids: Iterable[int],
    content: ContentFeatures,
) -> np.ndarray:
    """
    Construct a simple user preference vector in the same feature space as movies.

    This combines:
    - A binary vector from explicitly selected genres.
    - The average feature vector of liked movies.
    """
    n_features = content.feature_matrix.shape[1]
    user_vec = np.zeros(n_features, dtype=np.float32)

    # Contribution from selected genres
    genre_to_index: Dict[str, int] = {g: i for i, g in enumerate(content.feature_names)}
    for g in preferred_genres:
        idx = genre_to_index.get(g)
        if idx is not None:
            user_vec[idx] += 1.0

    # Contribution from liked movies
    liked_indices: List[int] = []
    for movie_id in liked_movie_ids:
        row = content.item_id_to_row.get(int(movie_id))
        if row is not None:
            liked_indices.append(row)

    if liked_indices:
        liked_matrix = content.feature_matrix[liked_indices, :]
        liked_mean = liked_matrix.mean(axis=0)
        user_vec += liked_mean

    # Normalize to unit length if possible
    norm = np.linalg.norm(user_vec)
    if norm > 0:
        user_vec = user_vec / norm

    return user_vec


def compute_content_scores(
    user_vector: np.ndarray,
    content: ContentFeatures,
) -> np.ndarray:
    """
    Compute cosine similarity between a user vector and all movie feature vectors.
    """
    if user_vector.ndim == 1:
        user_vec = user_vector.reshape(1, -1)
    else:
        user_vec = user_vector

    # Normalize movie features
    movie_feats = content.feature_matrix
    movie_norms = np.linalg.norm(movie_feats, axis=1, keepdims=True)
    movie_norms[movie_norms == 0] = 1.0
    movie_feats_normed = movie_feats / movie_norms

    scores = movie_feats_normed @ user_vec.T
    return scores.ravel()

