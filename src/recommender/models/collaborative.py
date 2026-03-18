"""
Item-based collaborative filtering.

Uses a user–item interaction matrix to compute item–item similarities,
then recommends items similar to the ones the user liked.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.metrics.pairwise import cosine_similarity

from .. import config
from ..preprocessing import InteractionData


class ItemItemRecommender:
    """
    Item–item collaborative filtering: recommend items similar to the user's liked items.
    """

    def __init__(
        self,
        interaction_data: InteractionData,
        n_similar: int = 50,
    ) -> None:
        """
        Parameters
        ----------
        interaction_data : InteractionData
            Preprocessed ratings, movies, and user–item matrix.
        n_similar : int
            Number of similar items to consider per liked item when aggregating scores.
        """
        self.interaction_data = interaction_data
        self.n_similar = n_similar
        self._item_similarity: Optional[sparse.csr_matrix] = None

    def fit(self, user_item_matrix: Optional[sparse.csr_matrix] = None) -> ItemItemRecommender:
        """
        Precompute item–item cosine similarity matrix.

        Parameters
        ----------
        user_item_matrix : sparse matrix, optional
            Shape (n_users, n_items). If None, uses interaction_data.user_item_matrix.

        Returns
        -------
        self
        """
        matrix = user_item_matrix if user_item_matrix is not None else self.interaction_data.user_item_matrix
        # Items as rows for similarity (each row = item's vector across users)
        item_user = matrix.T
        # Cosine similarity between items
        sim = cosine_similarity(item_user, dense_output=False)
        self._item_similarity = sparse.csr_matrix(sim)
        return self

    def recommend_for_liked_items(
        self,
        liked_item_ids: List[int],
        top_k: int = 20,
        exclude_movie_ids: Optional[Set[int]] = None,
    ) -> pd.DataFrame:
        """
        Recommend items most similar to the given liked items.

        Parameters
        ----------
        liked_item_ids : list of int
            Movie IDs the user liked.
        top_k : int
            Number of recommendations.
        exclude_movie_ids : set of int, optional
            Movie IDs to exclude (e.g. the liked ones).

        Returns
        -------
        pd.DataFrame
            Columns: movieId, title, genres, score, reason.
        """
        if self._item_similarity is None:
            self.fit()

        id_to_idx = self.interaction_data.item_id_to_index
        idx_to_id = self.interaction_data.index_to_item_id
        movies = self.interaction_data.movies

        # Map liked IDs to indices; skip if not in matrix
        liked_indices = [id_to_idx[mid] for mid in liked_item_ids if mid in id_to_idx]
        if not liked_indices:
            return _empty_recommendations()

        exclude_indices = set()
        if exclude_movie_ids:
            exclude_indices = {id_to_idx[mid] for mid in exclude_movie_ids if mid in id_to_idx}
        exclude_indices.update(liked_indices)

        n_items = self._item_similarity.shape[0]
        aggregate_scores = np.zeros(n_items, dtype=np.float64)

        for idx in liked_indices:
            row = self._item_similarity.getrow(idx).toarray().ravel()
            aggregate_scores += row

        aggregate_scores[list(exclude_indices)] = -np.inf
        top_indices = np.argsort(-aggregate_scores)[:top_k]
        top_indices = [i for i in top_indices if aggregate_scores[i] > -np.inf]

        if not top_indices:
            return _empty_recommendations()

        movie_ids = [idx_to_id[i] for i in top_indices]
        scores = aggregate_scores[top_indices]

        result = movies[movies[config.ITEM_ID_COL].isin(movie_ids)].set_index(config.ITEM_ID_COL).loc[movie_ids].reset_index()
        result["score"] = scores
        result["reason"] = "similar to movies you liked (collaborative filtering)"
        return result[[config.ITEM_ID_COL, config.TITLE_COL, config.GENRES_COL, "score", "reason"]]


def _empty_recommendations() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[config.ITEM_ID_COL, config.TITLE_COL, config.GENRES_COL, "score", "reason"]
    )
