"""
High-level API for the recommender: load artifacts and get recommendations.

Used by the Streamlit app so UI code stays thin and testable.
Supports loading from a precomputed pickle for faster app startup.
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pandas as pd

from . import config
from .data_loading import load_movielens
from .features import ContentFeatures, build_genre_features
from .models import HybridRecommender, PopularityRecommender, ItemItemRecommender, ContentRecommender
from .preprocessing import prepare_interaction_data

ARTIFACTS_CACHE_PATH: Path = config.PROCESSED_DATA_DIR / "artifacts.pkl"


@dataclass
class Artifacts:
    """
    All precomputed data and models needed to serve recommendations.

    Attributes
    ----------
    movies_df : pd.DataFrame
        Movies with columns movieId, title, genres (for display and mapping).
    available_genres : list of str
        Sorted list of genre names for the UI multiselect.
    hybrid_recommender : HybridRecommender
        The main recommender used for get_recommendations_for_user_preferences.
    """

    movies_df: pd.DataFrame
    available_genres: List[str]
    hybrid_recommender: HybridRecommender


def load_default_artifacts(
    ratings_path: Optional[Path] = None,
    movies_path: Optional[Path] = None,
    use_cache: bool = True,
) -> Artifacts:
    """
    Load MovieLens data, preprocess, train all sub-models, and return Artifacts.

    If use_cache is True and data/processed/artifacts.pkl exists, loads from
    that file for much faster startup. Run scripts/build_artifacts.py once to create it.
    """
    if use_cache and ARTIFACTS_CACHE_PATH.exists():
        try:
            with open(ARTIFACTS_CACHE_PATH, "rb") as f:
                return pickle.load(f)
        except Exception:
            pass

    ratings, movies = load_movielens()
    if ratings_path is not None or movies_path is not None:
        # If caller passed paths, we already loaded via load_movielens; here we ignore
        # and use default. Alternatively we could load from custom paths.
        pass

    interaction_data = prepare_interaction_data(ratings, movies)
    movies_df = interaction_data.movies

    baseline = PopularityRecommender(
        ratings=interaction_data.ratings,
        movies=movies_df,
    )
    item_item = ItemItemRecommender(interaction_data=interaction_data)
    item_item.fit()

    content_features = build_genre_features(movies_df)
    content_recommender = ContentRecommender(content_features=content_features)

    hybrid = HybridRecommender(
        baseline=baseline,
        collaborative=item_item,
        content=content_recommender,
        weight_baseline=0.2,
        weight_collab=0.5,
        weight_content=0.3,
    )

    available_genres = sorted(content_features.feature_names)

    return Artifacts(
        movies_df=movies_df,
        available_genres=available_genres,
        hybrid_recommender=hybrid,
    )


def save_artifacts(artifacts: Artifacts, path: Optional[Path] = None) -> None:
    """Save artifacts to a pickle file for fast loading. Use scripts/build_artifacts.py."""
    p = path or ARTIFACTS_CACHE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        pickle.dump(artifacts, f)


def get_recommendations_for_user_preferences(
    artifacts: Artifacts,
    preferred_genres: List[str],
    liked_movie_ids: List[int],
    top_k: int = 20,
) -> pd.DataFrame:
    """
    Return a DataFrame of recommended movies for the given preferences.

    Parameters
    ----------
    artifacts : Artifacts
        From load_default_artifacts().
    preferred_genres : list of str
        Genres the user likes.
    liked_movie_ids : list of int
        Movie IDs the user liked.
    top_k : int
        Number of recommendations.

    Returns
    -------
    pd.DataFrame
        Columns: movieId, title, genres, score, reason.
    """
    return artifacts.hybrid_recommender.recommend(
        preferred_genres=preferred_genres,
        liked_movie_ids=liked_movie_ids,
        top_k=top_k,
    )
