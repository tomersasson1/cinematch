from __future__ import annotations

from pathlib import Path
from typing import Tuple

import pandas as pd

from . import config


def _ensure_file_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Expected file not found at {path}. "
            "Make sure you downloaded MovieLens and placed ratings.csv and movies.csv "
            "under data/raw/movielens/."
        )


def load_ratings(path: Path | None = None) -> pd.DataFrame:
    """
    Load MovieLens ratings as a pandas DataFrame.

    Parameters
    ----------
    path:
        Optional path to ratings.csv. If not provided, uses config.RATINGS_FILE.
    """
    ratings_path = path or config.RATINGS_FILE
    _ensure_file_exists(ratings_path)

    ratings = pd.read_csv(ratings_path)
    expected_cols = {config.USER_ID_COL, config.ITEM_ID_COL, config.RATING_COL}
    missing = expected_cols.difference(ratings.columns)
    if missing:
        raise ValueError(f"Ratings file is missing expected columns: {missing}")
    return ratings


def load_movies(path: Path | None = None) -> pd.DataFrame:
    """
    Load MovieLens movies metadata as a pandas DataFrame.

    Parameters
    ----------
    path:
        Optional path to movies.csv. If not provided, uses config.MOVIES_FILE.
    """
    movies_path = path or config.MOVIES_FILE
    _ensure_file_exists(movies_path)

    movies = pd.read_csv(movies_path)
    expected_cols = {config.ITEM_ID_COL, config.TITLE_COL, config.GENRES_COL}
    missing = expected_cols.difference(movies.columns)
    if missing:
        raise ValueError(f"Movies file is missing expected columns: {missing}")
    return movies


def load_movielens() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Convenience function to load both ratings and movies.

    Returns
    -------
    ratings, movies : Tuple[pd.DataFrame, pd.DataFrame]
    """
    ratings = load_ratings()
    movies = load_movies()
    return ratings, movies

