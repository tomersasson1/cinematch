"""
Hybrid recommender that combines baseline, collaborative, and content-based scores.
"""

from __future__ import annotations

from typing import List, Optional, Set

import numpy as np
import pandas as pd

from .. import config
from .baseline import PopularityRecommender
from .collaborative import ItemItemRecommender
from .content import ContentRecommender
from ..features import ContentFeatures
from ..preprocessing import InteractionData


class HybridRecommender:
    """
    Combines popularity, collaborative filtering, and content-based scores
    via a weighted sum (after normalizing each score vector to [0, 1]).
    """

    def __init__(
        self,
        baseline: PopularityRecommender,
        collaborative: ItemItemRecommender,
        content: ContentRecommender,
        weight_baseline: float = 0.2,
        weight_collab: float = 0.5,
        weight_content: float = 0.3,
    ) -> None:
        self.baseline = baseline
        self.collaborative = collaborative
        self.content = content
        self.weight_baseline = weight_baseline
        self.weight_collab = weight_collab
        self.weight_content = weight_content

    def recommend(
        self,
        preferred_genres: List[str],
        liked_movie_ids: List[int],
        top_k: int = 20,
    ) -> pd.DataFrame:
        """
        Get hybrid recommendations by combining all three recommenders.

        - If the user has no liked movies, collaborative is skipped and
          baseline + content are combined.
        - Scores from each recommender are min-max normalized to [0, 1],
          then combined with the configured weights.
        """
        exclude = set(liked_movie_ids)

        # Baseline: genre-filtered popularity
        df_baseline = self.baseline.recommend(
            genres=preferred_genres or None,
            top_k=top_k * 3,
            exclude_movie_ids=exclude,
        )

        # Collaborative: only if user has liked movies
        if liked_movie_ids:
            df_collab = self.collaborative.recommend_for_liked_items(
                liked_item_ids=liked_movie_ids,
                top_k=top_k * 3,
                exclude_movie_ids=exclude,
            )
        else:
            df_collab = _empty_df()

        # Content
        df_content = self.content.recommend(
            preferred_genres=preferred_genres,
            liked_movie_ids=liked_movie_ids,
            top_k=top_k * 3,
            exclude_movie_ids=exclude,
        )

        # Build unified score: collect all candidate movie IDs
        all_ids = set()
        if not df_baseline.empty:
            all_ids.update(df_baseline[config.ITEM_ID_COL].tolist())
        if not df_collab.empty:
            all_ids.update(df_collab[config.ITEM_ID_COL].tolist())
        if not df_content.empty:
            all_ids.update(df_content[config.ITEM_ID_COL].tolist())

        if not all_ids:
            return _empty_df()

        scores = {}
        for mid in all_ids:
            scores[mid] = 0.0

        def add_scores(df: pd.DataFrame, w: float) -> None:
            if df.empty or w <= 0:
                return
            s = df.set_index(config.ITEM_ID_COL)["score"]
            min_s, max_s = s.min(), s.max()
            if max_s > min_s:
                norm = (s - min_s) / (max_s - min_s)
            else:
                norm = s * 0 + 1.0
            for mid, v in norm.items():
                scores[mid] = scores.get(mid, 0.0) + w * v

        add_scores(df_baseline, self.weight_baseline)
        add_scores(df_collab, self.weight_collab)
        add_scores(df_content, self.weight_content)

        # Sort by combined score and take top_k
        sorted_ids = sorted(scores.keys(), key=lambda m: -scores[m])[:top_k]
        movies = self.baseline.movies
        result = movies[movies[config.ITEM_ID_COL].isin(sorted_ids)].set_index(config.ITEM_ID_COL).loc[sorted_ids].reset_index()
        result["score"] = [scores[mid] for mid in sorted_ids]
        result["reason"] = "hybrid (popularity + collaborative + content)"
        return result[[config.ITEM_ID_COL, config.TITLE_COL, config.GENRES_COL, "score", "reason"]]


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[config.ITEM_ID_COL, config.TITLE_COL, config.GENRES_COL, "score", "reason"]
    )
