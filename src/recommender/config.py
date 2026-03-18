from __future__ import annotations

from pathlib import Path


PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
DATA_DIR: Path = PROJECT_ROOT / "data"
RAW_DATA_DIR: Path = DATA_DIR / "raw"
PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"

MOVIELENS_DIR: Path = RAW_DATA_DIR / "movielens"
RATINGS_FILE: Path = MOVIELENS_DIR / "ratings.csv"
MOVIES_FILE: Path = MOVIELENS_DIR / "movies.csv"

# Columns expected in MovieLens CSVs
USER_ID_COL: str = "userId"
ITEM_ID_COL: str = "movieId"
RATING_COL: str = "rating"
TITLE_COL: str = "title"
GENRES_COL: str = "genres"

# Preprocessing parameters (can be tuned later)
MIN_USER_RATINGS: int = 20
MIN_ITEM_RATINGS: int = 50

# Collaborative filtering parameters
MIN_RATING_FOR_LIKE: float = 4.0

