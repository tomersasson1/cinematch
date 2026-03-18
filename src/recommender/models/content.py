"""
Content-based recommender using genre (and optional) features.

Scores movies by similarity between the user's preference vector
and each movie's feature vector (e.g. multi-hot genres).
"""

from __future__ import annotations

from typing import List, Optional, Set

import numpy as np
import pandas as pd

from .. import config
from ..features import (
    ContentFeatures,
    build_user_preference_vector,
    compute_content_scores,
)


class ContentRecommender:
    """
    Content-based recommendations using genre (and optionally other) features.
    """

    def __init__(self, content_features: ContentFeatures) -> None:
        self.content = content_features

    def recommend(
        self,
        preferred_genres: List[str],
        liked_movie_ids: List[int],
        top_k: int = 20,
        exclude_movie_ids: Optional[Set[int]] = None,
    ) -> pd.DataFrame:
        """
        Recommend movies whose content best matches the user's preferences.

        Parameters
        ----------
        preferred_genres : list of str
            Genres the user likes.
        liked_movie_ids : list of int
            Movie IDs the user liked (used to build preference vector).
        top_k : int
            Number of recommendations.
        exclude_movie_ids : set of int, optional
            Movie IDs to exclude.

        Returns
        -------
        pd.DataFrame
            Columns: movieId, title, genres, score, reason.
        """
        user_vec = build_user_preference_vector(
            preferred_genres, liked_movie_ids, self.content
        )
        scores = compute_content_scores(user_vec, self.content)

        movie_ids = list(self.content.item_id_to_row.keys())
        row_to_id = {v: k for k, v in self.content.item_id_to_row.items()}

        exclude = set(exclude_movie_ids or []) | set(liked_movie_ids)
        candidates = [
            (row_to_id[i], scores[i])
            for i in range(len(movie_ids))
            if row_to_id[i] not in exclude
        ]
        candidates.sort(key=lambda x: -x[1])
        top = candidates[:top_k]

        if not top:
            return _empty_content_df()

        ids = [x[0] for x in top]
        sc = [x[1] for x in top]

        movies = self.content.movies
        result = movies[movies[config.ITEM_ID_COL].isin(ids)].set_index(config.ITEM_ID_COL).loc[ids].reset_index()
        result["score"] = sc
        result["reason"] = "matches your preferred genres and liked movies (content-based)"
        return result[[config.ITEM_ID_COL, config.TITLE_COL, config.GENRES_COL, "score", "reason"]]


def _empty_content_df() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[config.ITEM_ID_COL, config.TITLE_COL, config.GENRES_COL, "score", "reason"]
    )
