"""
Recommender package exposing high-level factory functions.

This package is organized into:
- config: paths and global parameters
- data_loading: reading raw MovieLens CSVs
- preprocessing: cleaning and building matrices / mappings
- features: content feature engineering (e.g. genres)
- models: different recommender model implementations
- interfaces: functions used by the UI to get recommendations
"""

from . import config, data_loading, preprocessing, features, evaluation, interfaces  # noqa: F401

