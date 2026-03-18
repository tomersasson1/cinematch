from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from scipy import sparse

from . import config


@dataclass
class InteractionData:
    """
    Container for preprocessed interaction data and mappings.

    Attributes
    ----------
    ratings:
        Filtered ratings DataFrame.
    movies:
        Filtered movies DataFrame (only items that appear in ratings).
    user_id_to_index:
        Mapping from original userId to matrix row index.
    item_id_to_index:
        Mapping from original movieId to matrix column index.
    index_to_user_id:
        Reverse mapping from row index to userId.
    index_to_item_id:
        Reverse mapping from column index to movieId.
    user_item_matrix:
        Sparse user–item matrix of implicit interactions.
    """

    ratings: pd.DataFrame
    movies: pd.DataFrame
    user_id_to_index: Dict[int, int]
    item_id_to_index: Dict[int, int]
    index_to_user_id: Dict[int, int]
    index_to_item_id: Dict[int, int]
    user_item_matrix: sparse.csr_matrix


def filter_ratings(
    ratings: pd.DataFrame,
    min_user_ratings: int = config.MIN_USER_RATINGS,
    min_item_ratings: int = config.MIN_ITEM_RATINGS,
) -> pd.DataFrame:
    """
    Filter out very inactive users and very unpopular items.
    """
    user_counts = ratings.groupby(config.USER_ID_COL)[config.ITEM_ID_COL].count()
    item_counts = ratings.groupby(config.ITEM_ID_COL)[config.USER_ID_COL].count()

    active_users = user_counts[user_counts >= min_user_ratings].index
    popular_items = item_counts[item_counts >= min_item_ratings].index

    filtered = ratings[
        ratings[config.USER_ID_COL].isin(active_users)
        & ratings[config.ITEM_ID_COL].isin(popular_items)
    ].copy()
    return filtered


def build_id_mappings(
    ratings: pd.DataFrame,
) -> Tuple[Dict[int, int], Dict[int, int], Dict[int, int], Dict[int, int]]:
    """
    Build mappings between original user / item IDs and matrix indices.
    """
    unique_user_ids = np.sort(ratings[config.USER_ID_COL].unique())
    unique_item_ids = np.sort(ratings[config.ITEM_ID_COL].unique())

    user_id_to_index = {uid: idx for idx, uid in enumerate(unique_user_ids)}
    item_id_to_index = {iid: idx for idx, iid in enumerate(unique_item_ids)}

    index_to_user_id = {idx: uid for uid, idx in user_id_to_index.items()}
    index_to_item_id = {idx: iid for iid, idx in item_id_to_index.items()}

    return user_id_to_index, item_id_to_index, index_to_user_id, index_to_item_id


def build_interaction_matrix(
    ratings: pd.DataFrame,
    user_id_to_index: Dict[int, int],
    item_id_to_index: Dict[int, int],
    threshold: float = config.MIN_RATING_FOR_LIKE,
) -> sparse.csr_matrix:
    """
    Build a sparse user–item matrix using implicit feedback.

    An entry is 1 if rating >= threshold, otherwise 0.
    """
    mask = ratings[config.RATING_COL] >= threshold
    implicit = ratings[mask]

    row_indices = implicit[config.USER_ID_COL].map(user_id_to_index).to_numpy()
    col_indices = implicit[config.ITEM_ID_COL].map(item_id_to_index).to_numpy()
    data = np.ones_like(row_indices, dtype=np.float32)

    n_users = len(user_id_to_index)
    n_items = len(item_id_to_index)

    matrix = sparse.csr_matrix((data, (row_indices, col_indices)), shape=(n_users, n_items))
    return matrix


def prepare_interaction_data(
    ratings: pd.DataFrame,
    movies: pd.DataFrame,
) -> InteractionData:
    """
    Run the full preprocessing pipeline and return interaction data.
    """
    filtered_ratings = filter_ratings(ratings)
    (
        user_id_to_index,
        item_id_to_index,
        index_to_user_id,
        index_to_item_id,
    ) = build_id_mappings(filtered_ratings)

    user_item_matrix = build_interaction_matrix(
        filtered_ratings, user_id_to_index, item_id_to_index
    )

    movies_filtered = movies[movies[config.ITEM_ID_COL].isin(item_id_to_index.keys())].copy()

    return InteractionData(
        ratings=filtered_ratings,
        movies=movies_filtered,
        user_id_to_index=user_id_to_index,
        item_id_to_index=item_id_to_index,
        index_to_user_id=index_to_user_id,
        index_to_item_id=index_to_item_id,
        user_item_matrix=user_item_matrix,
    )

