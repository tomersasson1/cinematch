"""
Popularity-based baseline recommender.

Always returns sensible recommendations by ranking movies by how often
they were rated (and optionally by average rating). Supports genre filtering.
"""

from __future__ import annotations

from typing import List, Optional, Set

import pandas as pd

from .. import config


class PopularityRecommender:
    """
    Recommends movies by popularity (number of ratings, optionally weighted by average rating).
    If genres are provided, only movies matching any of those genres are considered.
    """

    def __init__(
        self,
        ratings: pd.DataFrame,
        movies: pd.DataFrame,
        use_avg_rating: bool = True,
    ) -> None:
        """
        Parameters
        ----------
        ratings : pd.DataFrame
            Must contain columns: userId, movieId, rating.
        movies : pd.DataFrame
            Must contain columns: movieId, title, genres.
        use_avg_rating : bool
            If True, popularity score = count * (avg_rating / 5) so higher-rated movies rank higher.
        """
        self.ratings = ratings
        self.movies = movies
        self.use_avg_rating = use_avg_rating
        self._stats: Optional[pd.DataFrame] = None
        self._fit()

    def _fit(self) -> None:
        agg = self.ratings.groupby(config.ITEM_ID_COL)[config.RATING_COL].agg(["count", "mean"])
        agg.columns = ["count", "avg_rating"]
        if self.use_avg_rating:
            agg["score"] = agg["count"] * (agg["avg_rating"] / 5.0)
        else:
            agg["score"] = agg["count"].astype(float)
        self._stats = agg

    def recommend(
        self,
        genres: Optional[List[str]] = None,
        top_k: int = 20,
        exclude_movie_ids: Optional[Set[int]] = None,
    ) -> pd.DataFrame:
        """
        Return top-k movies by popularity, optionally filtered by genres.

        Parameters
        ----------
        genres : list of str, optional
            If provided, only movies that have at least one of these genres are considered.
        top_k : int
            Number of recommendations to return.
        exclude_movie_ids : set of int, optional
            Movie IDs to exclude from results (e.g. already liked).

        Returns
        -------
        pd.DataFrame
            Columns: movieId, title, genres, score, reason.
        """
        if self._stats is None:
            self._fit()

        candidates = self._stats.copy()
        candidates = candidates.join(
            self.movies.set_index(config.ITEM_ID_COL)[[config.TITLE_COL, config.GENRES_COL]],
            how="left",
        )
        candidates = candidates.reset_index()

        if genres:
            def has_genre(gs: str) -> bool:
                if pd.isna(gs):
                    return False
                g_set = {g.strip() for g in str(gs).split("|")}
                return bool(g_set & set(genres))

            candidates = candidates[candidates[config.GENRES_COL].apply(has_genre)]

        if exclude_movie_ids:
            candidates = candidates[~candidates[config.ITEM_ID_COL].isin(exclude_movie_ids)]

        candidates = candidates.nlargest(top_k, "score")
        candidates["reason"] = "popularity (baseline)"
        return candidates[[config.ITEM_ID_COL, config.TITLE_COL, config.GENRES_COL, "score", "reason"]]
