"""
TMDB (The Movie Database) API client for up-to-date movie data.

Requires a free API key from https://www.themoviedb.org/settings/api .
Set the environment variable TMDB_API_KEY or pass api_key to fetch functions.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

import requests

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


@dataclass
class TMDBMovie:
    """A movie from TMDB with display fields."""
    id: int
    title: str
    overview: Optional[str]
    release_date: Optional[str]
    vote_average: float
    poster_path: Optional[str]
    genre_names: List[str]

    @property
    def poster_url(self) -> Optional[str]:
        if self.poster_path:
            return f"{IMAGE_BASE}{self.poster_path}"
        return None


def _get_api_key() -> Optional[str]:
    return os.environ.get("TMDB_API_KEY", "").strip() or None


def _genre_id_to_name() -> Dict[int, str]:
    """TMDB genre IDs to names (English). Cached in module."""
    if not hasattr(_genre_id_to_name, "_cache"):
        _genre_id_to_name._cache = {
            28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
            80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
            14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
            9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
            10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western",
        }
    return _genre_id_to_name._cache


def get_genres_for_cards() -> List[tuple[int, str]]:
    """Return (genre_id, genre_name) sorted by name for UI genre cards."""
    m = _genre_id_to_name()
    return sorted(m.items(), key=lambda x: x[1])


def fetch_movies_by_genres(
    genre_ids: List[int],
    api_key: Optional[str] = None,
    limit: int = 24,
    min_year: Optional[int] = None,
) -> List[TMDBMovie]:
    """
    Fetch movies matching the given genres, sorted by popularity (most watched).
    Set min_year to restrict to newer movies; None = all years (most popular overall).
    """
    key = api_key or _get_api_key()
    if not key or not genre_ids:
        return []

    url = f"{BASE_URL}/discover/movie"
    # Use | for OR (any of these genres); comma would mean AND (all genres) and often returns empty
    params = {
        "api_key": key,
        "language": "en-US",
        "sort_by": "popularity.desc",
        "with_genres": "|".join(str(g) for g in genre_ids),
    }
    if min_year is not None:
        params["primary_release_date.gte"] = f"{min_year}-01-01"

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError, KeyError):
        return []

    results = data.get("results", [])[:limit]
    genre_map = _genre_id_to_name()
    movies = []
    for m in results:
        gids = m.get("genre_ids") or []
        genre_names = [genre_map.get(g, "") for g in gids if genre_map.get(g)]
        movies.append(TMDBMovie(
            id=m.get("id", 0),
            title=m.get("title", "Unknown"),
            overview=m.get("overview"),
            release_date=m.get("release_date"),
            vote_average=float(m.get("vote_average", 0)),
            poster_path=m.get("poster_path"),
            genre_names=genre_names,
        ))
    return movies


def fetch_movies_by_genres_any(
    genre_ids: List[int],
    api_key: Optional[str] = None,
    limit: int = 32,
    min_year: Optional[int] = None,
) -> List[TMDBMovie]:
    """
    Fetch movies that match ANY of the given genres (one request per genre, then merge).
    More reliable than with_genres when multiple genres are selected.
    """
    key = api_key or _get_api_key()
    if not key or not genre_ids:
        return []

    seen_ids: Set[int] = set()
    merged: List[TMDBMovie] = []
    per_genre = max(15, (limit + len(genre_ids) - 1) // len(genre_ids))

    for gid in genre_ids:
        batch = fetch_movies_by_genres([gid], api_key=key, limit=per_genre, min_year=min_year)
        for m in batch:
            if m.id not in seen_ids:
                seen_ids.add(m.id)
                merged.append(m)
                if len(merged) >= limit:
                    return merged[:limit]
    return merged[:limit]


def fetch_popular_movies(
    api_key: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
) -> List[TMDBMovie]:
    """
    Fetch currently popular movies from TMDB (updated regularly).
    Returns a list of TMDBMovie for display.
    """
    key = api_key or _get_api_key()
    if not key:
        return []

    url = f"{BASE_URL}/movie/popular"
    params = {"api_key": key, "language": "en-US", "page": page}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError, KeyError):
        return []

    results = data.get("results", [])[:limit]
    genre_map = _genre_id_to_name()
    movies = []
    for m in results:
        genre_ids = m.get("genre_ids") or []
        genre_names = [genre_map.get(g, "") for g in genre_ids if genre_map.get(g)]
        movies.append(TMDBMovie(
            id=m.get("id", 0),
            title=m.get("title", "Unknown"),
            overview=m.get("overview"),
            release_date=m.get("release_date"),
            vote_average=float(m.get("vote_average", 0)),
            poster_path=m.get("poster_path"),
            genre_names=genre_names,
        ))
    return movies


def fetch_now_playing(
    api_key: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
) -> List[TMDBMovie]:
    """Fetch movies currently in theatres (very up-to-date)."""
    key = api_key or _get_api_key()
    if not key:
        return []

    url = f"{BASE_URL}/movie/now_playing"
    params = {"api_key": key, "language": "en-US", "page": page}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError, KeyError):
        return []

    results = data.get("results", [])[:limit]
    genre_map = _genre_id_to_name()
    movies = []
    for m in results:
        genre_ids = m.get("genre_ids") or []
        genre_names = [genre_map.get(g, "") for g in genre_ids if genre_map.get(g)]
        movies.append(TMDBMovie(
            id=m.get("id", 0),
            title=m.get("title", "Unknown"),
            overview=m.get("overview"),
            release_date=m.get("release_date"),
            vote_average=float(m.get("vote_average", 0)),
            poster_path=m.get("poster_path"),
            genre_names=genre_names,
        ))
    return movies


def fetch_mixed_era_movies(
    genre_ids: List[int],
    api_key: Optional[str] = None,
    per_era: int = 10,
    page: int = 1,
) -> List[TMDBMovie]:
    """
    Fetch well-known movies across multiple decades for the given genres.

    Pulls from four era buckets (classics, 2000s, 2010s, recent) so the user
    sees a realistic spread of movies they might have actually watched.
    Results are sorted by vote_count descending (most-watched first) within
    each era, then interleaved so the final list feels varied.

    *page* offsets within each TMDB results page so the caller can paginate
    for a "Show me more" / refresh feature.
    """
    key = api_key or _get_api_key()
    if not key or not genre_ids:
        return []

    eras = [
        (None, 1999),       # classics (before 2000)
        (2000, 2009),       # 2000s
        (2010, 2019),       # 2010s
        (2020, None),       # recent
    ]

    url = f"{BASE_URL}/discover/movie"
    genre_str = "|".join(str(g) for g in genre_ids)
    buckets: List[List[TMDBMovie]] = []
    genre_map = _genre_id_to_name()

    for era_start, era_end in eras:
        params: Dict[str, Any] = {
            "api_key": key,
            "language": "en-US",
            "sort_by": "vote_count.desc",
            "vote_count.gte": 500,
            "with_genres": genre_str,
            "page": page,
        }
        if era_start is not None:
            params["primary_release_date.gte"] = f"{era_start}-01-01"
        if era_end is not None:
            params["primary_release_date.lte"] = f"{era_end}-12-31"

        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
        except (requests.RequestException, ValueError, KeyError):
            buckets.append([])
            continue

        results = data.get("results", [])[:per_era]
        era_movies: List[TMDBMovie] = []
        for m in results:
            gids = m.get("genre_ids") or []
            genre_names = [genre_map.get(g, "") for g in gids if genre_map.get(g)]
            era_movies.append(TMDBMovie(
                id=m.get("id", 0),
                title=m.get("title", "Unknown"),
                overview=m.get("overview"),
                release_date=m.get("release_date"),
                vote_average=float(m.get("vote_average", 0)),
                poster_path=m.get("poster_path"),
                genre_names=genre_names,
            ))
        buckets.append(era_movies)

    # Round-robin interleave so the grid mixes eras naturally
    seen: Set[int] = set()
    merged: List[TMDBMovie] = []
    max_len = max((len(b) for b in buckets), default=0)
    for i in range(max_len):
        for bucket in buckets:
            if i < len(bucket):
                m = bucket[i]
                if m.id not in seen:
                    seen.add(m.id)
                    merged.append(m)
    return merged


def get_poster_url_for_title(title: str, api_key: Optional[str] = None) -> Optional[str]:
    """
    Search TMDB by movie title and return the poster URL of the first result.
    Useful for MovieLens recommendations that don't have poster data.
    """
    key = api_key or _get_api_key()
    if not key or not title or not str(title).strip():
        return None
    query = str(title).strip()
    url = f"{BASE_URL}/search/movie"
    params = {"api_key": key, "language": "en-US", "query": query}
    try:
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        data = r.json()
    except (requests.RequestException, ValueError, KeyError):
        return None
    results = data.get("results", [])
    if not results:
        return None
    poster_path = results[0].get("poster_path")
    if not poster_path:
        return None
    return f"{IMAGE_BASE}{poster_path}"


__all__ = [
    "TMDBMovie",
    "get_genres_for_cards",
    "fetch_movies_by_genres",
    "fetch_movies_by_genres_any",
    "fetch_mixed_era_movies",
    "fetch_popular_movies",
    "fetch_now_playing",
    "get_poster_url_for_title",
]
