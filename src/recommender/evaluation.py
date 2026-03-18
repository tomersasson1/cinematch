"""
Offline evaluation metrics for recommenders: Precision@K, Recall@K, MAP@K.

Used in notebooks or scripts to compare baseline, CF, content, and hybrid models.
"""

from __future__ import annotations

from typing import Dict, List, Set

import numpy as np
import pandas as pd


def precision_at_k(recommended: List[int], relevant: Set[int], k: int) -> float:
    """
    Precision@K = (number of relevant in top-K) / k.

    Parameters
    ----------
    recommended : list of int
        Ordered list of recommended item IDs (top first).
    relevant : set of int
        Ground-truth relevant item IDs.
    k : int
        Cut-off.
    """
    top_k = recommended[:k]
    if not top_k:
        return 0.0
    hits = len(set(top_k) & relevant)
    return hits / k


def recall_at_k(recommended: List[int], relevant: Set[int], k: int) -> float:
    """
    Recall@K = (number of relevant in top-K) / |relevant|.
    """
    if not relevant:
        return 0.0
    top_k = recommended[:k]
    hits = len(set(top_k) & relevant)
    return hits / len(relevant)


def average_precision_at_k(recommended: List[int], relevant: Set[int], k: int) -> float:
    """
    Average Precision @ K: average of precision at each relevant hit in top-K.
    """
    if not relevant:
        return 0.0
    top_k = recommended[:k]
    hits = [i for i, item in enumerate(top_k) if item in relevant]
    if not hits:
        return 0.0
    precisions = [
        len([h for h in hits if h <= i]) / (i + 1)
        for i in hits
    ]
    return np.mean(precisions)


def map_at_k(
    per_user_recommended: Dict[int, List[int]],
    per_user_relevant: Dict[int, Set[int]],
    k: int,
) -> float:
    """
    Mean Average Precision @ K across users.
    """
    aps = [
        average_precision_at_k(rec, per_user_relevant.get(uid, set()), k)
        for uid, rec in per_user_recommended.items()
    ]
    return float(np.mean(aps)) if aps else 0.0


def evaluate_holdout(
    recommended: List[int],
    holdout_relevant: Set[int],
    k: int = 20,
) -> Dict[str, float]:
    """
    Compute Precision@K, Recall@K, and AP@K for one user.
    """
    return {
        f"precision@{k}": precision_at_k(recommended, holdout_relevant, k),
        f"recall@{k}": recall_at_k(recommended, holdout_relevant, k),
        f"ap@{k}": average_precision_at_k(recommended, holdout_relevant, k),
    }
