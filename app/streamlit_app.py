"""
Movie recommendation app with a dark cinematic UI and user profile persistence.

Flow: pick genres -> browse well-known movies across all decades -> like some -> get recs.
Returning users see their saved profile and can jump straight to recommendations.
Recommendations are interactive: mark as "Seen it" or "Not for me" and refresh.
"""

import json
import os
import random
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

_APP_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _APP_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

PROFILES_DIR = _PROJECT_ROOT / "data" / "user_profiles"


def _load_dotenv() -> None:
    env_file = _PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k:
                    os.environ[k] = v


import streamlit as st

from recommender import interfaces
from recommender.tmdb_client import (
    TMDBMovie,
    fetch_movies_by_genres,
    fetch_mixed_era_movies,
    get_genres_for_cards,
    get_poster_url_for_title,
)

TMDB_TO_MOVIELENS_GENRE = {"Science Fiction": "Sci-Fi"}
MOVIES_PER_PAGE = 20

# ---------------------------------------------------------------------------
# Title formatting: "Matrix, The (1999)" -> "The Matrix (1999)"
# ---------------------------------------------------------------------------
_TITLE_ARTICLE_RE = re.compile(
    r"^(.+),\s+(The|A|An|Le|La|Les|Das|Der|Die|El|Los|Las)\s*(\(\d{4}\))$",
    re.IGNORECASE,
)


def _fix_title(raw: str) -> str:
    m = _TITLE_ARTICLE_RE.match(raw.strip())
    if m:
        return f"{m.group(2)} {m.group(1)} {m.group(3)}"
    return raw.strip()


# ---------------------------------------------------------------------------
# Recommendation item dataclass (serialisable for session state)
# ---------------------------------------------------------------------------
@dataclass
class RecItem:
    title: str
    display_title: str
    genres: str
    poster_url: Optional[str]
    reason: str
    source: str  # "engine" or "tmdb"
    tmdb_id: Optional[int] = None


# ---------------------------------------------------------------------------
# SVG poster placeholder
# ---------------------------------------------------------------------------
_GENRE_ICONS: Dict[str, str] = {
    "Action": "\u2694\ufe0f", "Adventure": "\U0001f5fa\ufe0f", "Animation": "\U0001f3a8",
    "Comedy": "\U0001f602", "Crime": "\U0001f575\ufe0f", "Documentary": "\U0001f4f9",
    "Drama": "\U0001f3ad", "Family": "\U0001f46a", "Fantasy": "\U0001f9d9",
    "History": "\U0001f3db\ufe0f", "Horror": "\U0001f47b", "Music": "\U0001f3b5",
    "Mystery": "\U0001f50d", "Romance": "\u2764\ufe0f", "Sci-Fi": "\U0001f680",
    "Science Fiction": "\U0001f680", "Thriller": "\U0001f5e1\ufe0f", "War": "\u2699\ufe0f",
    "Western": "\U0001f920", "TV Movie": "\U0001f4fa", "IMAX": "\U0001f39e\ufe0f",
}
_GRADIENT_PAIRS = [
    ("#1a1a3e", "#2d1b69"), ("#1b2838", "#0f2b44"), ("#1a0a2e", "#2d1054"),
    ("#0d2137", "#1a3a5c"), ("#1a1a2e", "#2e1a4a"), ("#0f1b2d", "#1d3557"),
]


def _poster_placeholder_svg(title: str, genres: str = "") -> str:
    genre_list = [g.strip() for g in genres.replace("|", ",").split(",") if g.strip()] if genres else []
    icon = "\U0001f3ac"
    for g in genre_list:
        if g in _GENRE_ICONS:
            icon = _GENRE_ICONS[g]
            break
    idx = hash(title) % len(_GRADIENT_PAIRS)
    c1, c2 = _GRADIENT_PAIRS[idx]
    safe_title = title[:30].replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 450" '
        f'style="width:100%;aspect-ratio:2/3;display:block;border-radius:8px;">'
        f'<defs><linearGradient id="bg{idx}" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{c1}"/>'
        f'<stop offset="100%" stop-color="{c2}"/>'
        f'</linearGradient></defs>'
        f'<rect width="300" height="450" fill="url(#bg{idx})"/>'
        f'<text x="150" y="190" text-anchor="middle" font-size="64">{icon}</text>'
        f'<text x="150" y="260" text-anchor="middle" font-family="Inter,system-ui,sans-serif" '
        f'font-size="16" font-weight="600" fill="#c5c8d4">{safe_title}</text>'
        f'</svg>'
    )


# ---------------------------------------------------------------------------
# User profile persistence
# ---------------------------------------------------------------------------
def _profile_path(username: str) -> Path:
    return PROFILES_DIR / f"{username.strip().lower()}.json"


def _save_profile(username: str, data: Dict[str, Any]) -> None:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    _profile_path(username).write_text(
        json.dumps(data, indent=2, default=_json_default), encoding="utf-8",
    )


def _load_profile(username: str) -> Optional[Dict[str, Any]]:
    p = _profile_path(username)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _list_profiles() -> List[str]:
    if not PROFILES_DIR.exists():
        return []
    return sorted(p.stem for p in PROFILES_DIR.glob("*.json"))


def _json_default(obj: Any) -> Any:
    if isinstance(obj, set):
        return list(obj)
    raise TypeError


def _profile_to_session(profile: Dict[str, Any]) -> None:
    st.session_state["selected_genre_ids"] = set(profile.get("genre_ids", []))
    st.session_state["liked_tmdb_ids"] = set(profile.get("liked_tmdb_ids", []))
    st.session_state["liked_tmdb_titles"] = list(profile.get("liked_tmdb_titles", []))
    st.session_state["liked_movielens_titles"] = list(profile.get("liked_movielens_titles", []))
    st.session_state["dismissed_titles"] = set(profile.get("dismissed_titles", []))


def _session_to_profile_data() -> Dict[str, Any]:
    return {
        "genre_ids": list(st.session_state.get("selected_genre_ids", set())),
        "liked_tmdb_ids": list(st.session_state.get("liked_tmdb_ids", set())),
        "liked_tmdb_titles": list(st.session_state.get("liked_tmdb_titles", [])),
        "liked_movielens_titles": list(st.session_state.get("liked_movielens_titles", [])),
        "dismissed_titles": list(st.session_state.get("dismissed_titles", set())),
    }


# ---------------------------------------------------------------------------
# Dark cinematic theme
# ---------------------------------------------------------------------------
PAGE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
.stApp {
    background: linear-gradient(168deg, #0d0d1a 0%, #141428 40%, #0f1923 100%);
    font-family: 'Inter', sans-serif;
}
[data-testid="stSidebar"] { background: #12122a; }
[data-testid="stSidebar"] .stMarkdown { color: #c5c8d4; }
#MainMenu, footer, header { visibility: hidden; }
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #3a3a5c; border-radius: 3px; }

.main-title {
    font-size: 2.6rem; font-weight: 700; text-align: center;
    background: linear-gradient(135deg, #a78bfa, #60a5fa, #38bdf8);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 1.2rem 0 0.3rem; letter-spacing: -0.02em;
}
.subtitle { text-align: center; color: #8b8fa8; font-size: 1rem; margin-bottom: 2.2rem; }
.section-label {
    font-size: 1.05rem; font-weight: 600; color: #d1d5e4;
    margin: 1.5rem 0 0.7rem; letter-spacing: 0.01em;
}

/* welcome card */
.welcome-card {
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px; padding: 1.8rem 2rem; margin: 1rem auto 2rem;
    max-width: 560px; text-align: center;
}
.welcome-card h3 { color: #e4e6f0; font-size: 1.3rem; font-weight: 600; margin: 0 0 0.5rem; }
.welcome-card p { color: #8b8fa8; font-size: 0.9rem; margin: 0.3rem 0; }
.welcome-card .profile-stat {
    display: inline-block; background: rgba(167,139,250,.12);
    color: #a78bfa; font-size: 0.78rem; font-weight: 600;
    padding: 0.2rem 0.65rem; border-radius: 999px; margin: 0.15rem 0.2rem;
}

/* movie cards */
.movie-card {
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px; overflow: hidden;
    transition: transform .2s, border-color .25s, box-shadow .25s; position: relative;
}
.movie-card:hover {
    transform: translateY(-4px); border-color: rgba(167,139,250,.35);
    box-shadow: 0 8px 30px rgba(99,102,241,.15);
}
.movie-card.liked { border-color: #a78bfa; box-shadow: 0 0 0 2px rgba(167,139,250,0.4); }
.movie-poster { width: 100%; aspect-ratio: 2/3; object-fit: cover; display: block; }
.movie-info { padding: 0.6rem 0.75rem 0.5rem; }
.movie-title {
    font-size: 0.88rem; font-weight: 600; color: #e4e6f0;
    margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.movie-meta { font-size: 0.75rem; color: #7b7f96; margin: 0.2rem 0 0; }
.era-badge {
    position: absolute; top: 8px; left: 8px; font-size: 0.65rem; font-weight: 700;
    letter-spacing: 0.03em; padding: 0.15rem 0.45rem; border-radius: 6px;
    backdrop-filter: blur(6px);
}
.era-classic { background: rgba(251,191,36,.25); color: #fbbf24; }
.era-2000s   { background: rgba(52,211,153,.2);  color: #34d399; }
.era-2010s   { background: rgba(96,165,250,.2);  color: #60a5fa; }
.era-recent  { background: rgba(167,139,250,.2); color: #a78bfa; }

/* recommendation cards */
.rec-card {
    display: flex; align-items: flex-start; gap: 1rem;
    background: rgba(255,255,255,0.035); border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px; padding: 0.85rem 1rem; margin-bottom: 0.65rem;
    transition: border-color .2s, box-shadow .2s;
}
.rec-card:hover {
    border-color: rgba(96,165,250,.35); box-shadow: 0 4px 20px rgba(96,165,250,.1);
}
.rec-poster-wrap { width: 70px; flex-shrink: 0; }
.rec-poster-wrap img { width: 100%; border-radius: 8px; display: block; }
.rec-body { flex: 1; min-width: 0; }
.rec-rank {
    display: inline-block; font-size: 0.7rem; font-weight: 700; color: #a78bfa;
    background: rgba(167,139,250,.12); padding: 0.15rem 0.5rem;
    border-radius: 999px; margin-bottom: 0.25rem;
}
.rec-title {
    font-size: 0.95rem; font-weight: 600; color: #e4e6f0; margin: 0.15rem 0 0.15rem;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.rec-meta { font-size: 0.78rem; color: #7b7f96; margin: 0; }
.rec-reason { font-size: 0.72rem; color: #6366f1; margin-top: 0.25rem; font-style: italic; }

/* badges */
.liked-badge {
    display: inline-block; background: rgba(167,139,250,.15);
    color: #a78bfa; font-weight: 600; font-size: 0.82rem;
    padding: 0.3rem 0.9rem; border-radius: 999px; margin-top: 0.5rem;
}
.page-badge {
    display: inline-block; background: rgba(255,255,255,0.06);
    color: #7b7f96; font-size: 0.78rem; font-weight: 500;
    padding: 0.2rem 0.7rem; border-radius: 999px;
}
.feedback-count {
    display: inline-block; font-size: 0.82rem; font-weight: 500;
    padding: 0.25rem 0.8rem; border-radius: 999px; margin: 0.15rem 0.25rem;
}
.fb-seen { background: rgba(52,211,153,.12); color: #34d399; }
.fb-skip { background: rgba(248,113,113,.12); color: #f87171; }

/* buttons */
.stButton > button {
    font-weight: 600; border: none; border-radius: 10px;
    padding: 0.55rem 1.4rem; transition: transform .15s, box-shadow .15s;
}
.stButton > button:hover { transform: translateY(-1px); }
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, #7c3aed, #6366f1);
    color: #fff; box-shadow: 0 4px 14px rgba(99,102,241,.35);
}
.stButton > button[kind="primary"]:hover, .stButton > button[data-testid="stBaseButton-primary"]:hover {
    box-shadow: 0 6px 20px rgba(99,102,241,.5);
}
.stButton > button[kind="secondary"], .stButton > button[data-testid="stBaseButton-secondary"] {
    background: rgba(255,255,255,0.06); color: #c5c8d4; border: 1px solid rgba(255,255,255,0.1);
}
.stButton > button[kind="secondary"]:hover, .stButton > button[data-testid="stBaseButton-secondary"]:hover {
    background: rgba(255,255,255,0.1);
}
hr { border-color: rgba(255,255,255,0.06) !important; }
.stSlider [data-baseweb="slider"] div[role="slider"] { background: #7c3aed !important; }
.stSpinner > div { border-top-color: #a78bfa !important; }
.step-indicator {
    display: inline-flex; align-items: center; gap: 0.5rem;
    font-size: 0.82rem; font-weight: 600; color: #6366f1; margin-bottom: 0.3rem;
}
.step-dot { width: 8px; height: 8px; border-radius: 50%; background: #6366f1; display: inline-block; }
.step-dot.inactive { background: #3a3a5c; }
.empty-state { text-align: center; padding: 2.5rem 1rem; color: #6b6f85; font-size: 0.95rem; }
.empty-state .icon { font-size: 2.5rem; margin-bottom: 0.5rem; }
</style>
"""


# ---------------------------------------------------------------------------
# TMDB data helpers (cached)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def _tmdb_mixed_era(genre_ids: List[int], page: int) -> List[TMDBMovie]:
    if not genre_ids:
        return []
    return fetch_mixed_era_movies(genre_ids, per_era=10, page=page)


@st.cache_data(ttl=3600, show_spinner=False)
def _tmdb_new_for_genres(genre_ids: List[int], limit: int = 20) -> List[TMDBMovie]:
    if not genre_ids:
        return []
    return fetch_movies_by_genres(genre_ids, limit=limit, min_year=2019)


@st.cache_data(ttl=86400, show_spinner=False)
def _poster_for_title(title: str) -> Optional[str]:
    return get_poster_url_for_title(title)


@st.cache_resource
def _get_artifacts():
    return interfaces.load_default_artifacts()


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------
def _ensure_state():
    defaults: Dict[str, Any] = {
        "phase": "login",
        "username": "",
        "selected_genre_ids": set(),
        "liked_tmdb_ids": set(),
        "liked_tmdb_titles": [],
        "liked_movielens_titles": [],
        "dismissed_titles": set(),
        "movie_page": 1,
        "rec_items": [],
        "rec_generated": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _toggle_genre(gid: int) -> None:
    s = st.session_state["selected_genre_ids"]
    s.discard(gid) if gid in s else s.add(gid)


def _toggle_like(movie: TMDBMovie) -> None:
    s = st.session_state["liked_tmdb_ids"]
    t = st.session_state["liked_tmdb_titles"]
    if movie.id in s:
        s.discard(movie.id)
        if movie.title in t:
            t.remove(movie.title)
    else:
        s.add(movie.id)
        if movie.title not in t:
            t.append(movie.title)


def _extract_year(title: str) -> str:
    m = re.search(r"\((\d{4})\)\s*$", title)
    return m.group(1) if m else ""


def _era_badge(release_date: str | None) -> str:
    if not release_date:
        return ""
    try:
        year = int(release_date[:4])
    except (ValueError, TypeError):
        return ""
    if year < 2000:
        return '<span class="era-badge era-classic">CLASSIC</span>'
    if year < 2010:
        return '<span class="era-badge era-2000s">2000s</span>'
    if year < 2020:
        return '<span class="era-badge era-2010s">2010s</span>'
    return '<span class="era-badge era-recent">NEW</span>'


def _auto_save() -> None:
    username = st.session_state.get("username", "")
    if username:
        _save_profile(username, _session_to_profile_data())


def _mark_seen(title: str) -> None:
    """Add a recommended movie to the user's liked bank."""
    t = st.session_state["liked_tmdb_titles"]
    if title not in t:
        t.append(title)
    items: list = st.session_state["rec_items"]
    st.session_state["rec_items"] = [r for r in items if r["title"] != title]
    _auto_save()


def _mark_not_for_me(title: str) -> None:
    """Dismiss a recommendation so it won't appear again."""
    st.session_state["dismissed_titles"].add(title)
    items: list = st.session_state["rec_items"]
    st.session_state["rec_items"] = [r for r in items if r["title"] != title]
    _auto_save()


# ---------------------------------------------------------------------------
# Recommendation engine
# ---------------------------------------------------------------------------
def _generate_recs(top_k: int) -> List[Dict[str, Any]]:
    """Run the recommendation engine and return a list of RecItem dicts."""
    artifacts = _get_artifacts()
    st.session_state["artifacts_loaded"] = True

    id_to_name = dict(get_genres_for_cards())
    raw_names = sorted(
        id_to_name[g] for g in st.session_state["selected_genre_ids"]
    ) if st.session_state["selected_genre_ids"] else []
    preferred_genres = [TMDB_TO_MOVIELENS_GENRE.get(n, n) for n in raw_names]

    liked_movielens_ids: List[int] = []
    if st.session_state.get("liked_movielens_titles"):
        liked_movielens_ids = artifacts.movies_df.loc[
            artifacts.movies_df["title"].isin(st.session_state["liked_movielens_titles"]),
            "movieId",
        ].tolist()

    tmdb_liked_titles: List[str] = list(st.session_state.get("liked_tmdb_titles", []))
    if tmdb_liked_titles:
        ml_titles_lower = {
            re.sub(r"\s*\(\d{4}\)\s*$", "", t).strip().lower(): t
            for t in artifacts.movies_df["title"].tolist()
        }
        for tmdb_title in tmdb_liked_titles:
            clean = tmdb_title.strip().lower()
            ml_match = ml_titles_lower.get(clean)
            if ml_match:
                mid = artifacts.movies_df.loc[
                    artifacts.movies_df["title"] == ml_match, "movieId"
                ]
                if not mid.empty:
                    liked_movielens_ids.append(int(mid.iloc[0]))
    liked_movielens_ids = list(set(liked_movielens_ids))

    recs = interfaces.get_recommendations_for_user_preferences(
        artifacts=artifacts,
        preferred_genres=preferred_genres,
        liked_movie_ids=liked_movielens_ids,
        top_k=top_k + 20,
    )

    new_movies: List[TMDBMovie] = []
    if st.session_state["selected_genre_ids"]:
        new_movies = _tmdb_new_for_genres(
            list(st.session_state["selected_genre_ids"]),
            limit=min(top_k, 15),
        )
    liked_ids_set: Set[int] = st.session_state["liked_tmdb_ids"]
    new_movies = [m for m in new_movies if m.id not in liked_ids_set]

    rec_titles_lower = set()
    if not recs.empty:
        rec_titles_lower = {
            re.sub(r"\s*\(\d{4}\)\s*$", "", str(t)).strip().lower()
            for t in recs["title"]
        }
    new_movies = [
        m for m in new_movies if m.title.strip().lower() not in rec_titles_lower
    ]

    dismissed: Set[str] = st.session_state.get("dismissed_titles", set())
    liked_titles_lower = {t.strip().lower() for t in tmdb_liked_titles}

    items: List[Dict[str, Any]] = []

    rec_rows = list(recs.iterrows()) if not recs.empty else []
    rec_idx = 0
    tmdb_idx = 0
    slot = 1

    while rec_idx < len(rec_rows) or tmdb_idx < len(new_movies):
        if slot % 5 == 0 and tmdb_idx < len(new_movies):
            m = new_movies[tmdb_idx]
            tmdb_idx += 1
            if m.title in dismissed or m.title.strip().lower() in liked_titles_lower:
                slot += 1
                continue
            meta = f"{m.release_date or '\u2014'}  \u00b7  \u2605 {m.vote_average:.1f}  \u00b7  {' \u00b7 '.join(m.genre_names[:3])}"
            items.append({
                "title": m.title,
                "display_title": m.title,
                "meta": meta,
                "poster_url": m.poster_url,
                "reason": "new & trending",
                "genres": ", ".join(m.genre_names[:3]),
                "source": "tmdb",
            })
        elif rec_idx < len(rec_rows):
            _, row = rec_rows[rec_idx]
            rec_idx += 1
            raw_title = str(row["title"])
            display_title = _fix_title(raw_title)
            if raw_title in dismissed or display_title in dismissed:
                continue
            if display_title.strip().lower() in liked_titles_lower:
                continue
            poster_url = _poster_for_title(raw_title)
            year = _extract_year(raw_title)
            genres_raw = str(row["genres"])
            genres_str = genres_raw.replace("|", " \u00b7 ")
            meta_parts = [genres_str]
            if year:
                meta_parts.insert(0, year)
            meta = "  \u00b7  ".join(meta_parts)
            reason = str(row.get("reason", ""))
            items.append({
                "title": raw_title,
                "display_title": display_title,
                "meta": meta,
                "poster_url": poster_url,
                "reason": reason,
                "genres": genres_raw,
                "source": "engine",
            })
        else:
            m = new_movies[tmdb_idx]
            tmdb_idx += 1
            if m.title in dismissed or m.title.strip().lower() in liked_titles_lower:
                continue
            meta = f"{m.release_date or '\u2014'}  \u00b7  \u2605 {m.vote_average:.1f}  \u00b7  {' \u00b7 '.join(m.genre_names[:3])}"
            items.append({
                "title": m.title,
                "display_title": m.title,
                "meta": meta,
                "poster_url": m.poster_url,
                "reason": "new & trending",
                "genres": ", ".join(m.genre_names[:3]),
                "source": "tmdb",
            })
        slot += 1
        if len(items) >= top_k:
            break

    return items[:top_k]


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------
def _render_step_dots(current: int, total: int = 3) -> str:
    dots = "".join(
        f'<span class="step-dot{"" if i < current else " inactive"}"></span>'
        for i in range(total)
    )
    labels = ["Genres", "Movies", "Recommendations"]
    return f'<div class="step-indicator">{dots} Step {current} of {total} \u2014 {labels[current - 1]}</div>'


def _movie_card_html(
    poster_url: str | None, title: str, meta: str, liked: bool,
    release_date: str | None = None,
) -> str:
    cls = "movie-card liked" if liked else "movie-card"
    badge = _era_badge(release_date)
    if poster_url:
        poster_html = f'<img class="movie-poster" src="{poster_url}" alt="{title}" loading="lazy"/>'
    else:
        poster_html = _poster_placeholder_svg(title)
    return (
        f'<div class="{cls}">{badge}{poster_html}'
        f'<div class="movie-info">'
        f'<p class="movie-title" title="{title}">{title}</p>'
        f'<p class="movie-meta">{meta}</p>'
        f"</div></div>"
    )


def _rec_card_html(
    rank: int, poster_url: str | None, title: str, meta: str,
    reason: str = "", genres: str = "",
) -> str:
    if poster_url:
        poster_html = f'<img src="{poster_url}" alt="{title}" loading="lazy"/>'
    else:
        poster_html = _poster_placeholder_svg(title, genres)
    reason_html = f'<p class="rec-reason">{reason}</p>' if reason else ""
    return (
        f'<div class="rec-card">'
        f'<div class="rec-poster-wrap">{poster_html}</div>'
        f'<div class="rec-body">'
        f'<span class="rec-rank">#{rank}</span>'
        f'<p class="rec-title" title="{title}">{title}</p>'
        f'<p class="rec-meta">{meta}</p>'
        f"{reason_html}"
        f"</div></div>"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    _load_dotenv()
    st.set_page_config(
        page_title="CineMatch \u2014 Movie Recommendations",
        page_icon="\U0001f3ac",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _ensure_state()
    st.markdown(PAGE_CSS, unsafe_allow_html=True)
    st.markdown('<h1 class="main-title">CineMatch</h1>', unsafe_allow_html=True)

    # ==================================================================
    # LOGIN
    # ==================================================================
    if st.session_state["phase"] == "login":
        st.markdown(
            '<p class="subtitle">Your personal movie recommendation engine</p>',
            unsafe_allow_html=True,
        )
        existing = _list_profiles()
        col_l, col_m, col_r = st.columns([1.5, 2, 1.5])
        with col_m:
            name = st.text_input(
                "Enter your name to get started",
                placeholder="e.g. Alex",
                key="login_name",
                label_visibility="collapsed",
            )
            if existing:
                st.markdown(
                    '<p style="color:#7b7f96;font-size:0.82rem;margin:0.8rem 0 0.3rem;">Or continue as:</p>',
                    unsafe_allow_html=True,
                )
                for prof_name in existing:
                    if st.button(f"\u2192 {prof_name.title()}", key=f"prof_{prof_name}", type="secondary"):
                        profile = _load_profile(prof_name)
                        if profile:
                            st.session_state["username"] = prof_name
                            _profile_to_session(profile)
                            st.session_state["phase"] = "welcome_back"
                            st.rerun()
            st.markdown("")
            if st.button("Get started", type="primary", key="login_go",
                         disabled=not (name and name.strip())):
                clean_name = name.strip().lower()
                st.session_state["username"] = clean_name
                profile = _load_profile(clean_name)
                if profile:
                    _profile_to_session(profile)
                    st.session_state["phase"] = "welcome_back"
                else:
                    st.session_state["phase"] = "genres"
                st.rerun()
        return

    # ==================================================================
    # WELCOME BACK
    # ==================================================================
    if st.session_state["phase"] == "welcome_back":
        username = st.session_state["username"]
        id_to_name = dict(get_genres_for_cards())
        genre_names = sorted(
            id_to_name.get(g, str(g)) for g in st.session_state["selected_genre_ids"]
        )
        n_liked = len(st.session_state["liked_tmdb_ids"]) + len(st.session_state.get("liked_tmdb_titles", []))
        n_liked = max(len(st.session_state["liked_tmdb_ids"]), len(st.session_state.get("liked_tmdb_titles", [])))
        n_dismissed = len(st.session_state.get("dismissed_titles", set()))

        genre_badges = " ".join(
            f'<span class="profile-stat">{g}</span>' for g in genre_names
        ) if genre_names else '<span class="profile-stat">none yet</span>'

        stats_html = f'{n_liked} liked movie{"s" if n_liked != 1 else ""}'
        if n_dismissed:
            stats_html += f' \u00b7 {n_dismissed} dismissed'

        st.markdown(
            f'<div class="welcome-card">'
            f'<h3>Welcome back, {username.title()}!</h3>'
            f'<p>Your genres: {genre_badges}</p>'
            f'<p style="margin-top:0.4rem;">{stats_html}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns([1.2, 1.2, 1.2])
        with c1:
            if st.button("\u2728 Get recommendations", type="primary", key="wb_recs"):
                st.session_state["phase"] = "movies"
                st.session_state["movie_page"] = 1
                st.rerun()
        with c2:
            if st.button("\u270f\ufe0f Update my tastes", type="secondary", key="wb_edit"):
                st.session_state["phase"] = "genres"
                st.rerun()
        with c3:
            if st.button("\U0001f464 Switch user", type="secondary", key="wb_switch"):
                st.session_state["phase"] = "login"
                st.session_state["username"] = ""
                st.rerun()
        return

    # ------------------------------------------------------------------
    selected_ids: set = st.session_state["selected_genre_ids"]
    id_to_name = dict(get_genres_for_cards())
    selected_names = sorted(id_to_name[g] for g in selected_ids) if selected_ids else []
    genres_list = get_genres_for_cards()

    # ==================================================================
    # PHASE 1 — Genre selection
    # ==================================================================
    if st.session_state["phase"] == "genres":
        st.markdown(_render_step_dots(1), unsafe_allow_html=True)
        st.markdown(
            '<p class="subtitle">Tell us what you\'re in the mood for.</p>',
            unsafe_allow_html=True,
        )
        st.markdown('<p class="section-label">Pick your favorite genres</p>', unsafe_allow_html=True)

        cols = st.columns(5)
        for i, (gid, gname) in enumerate(genres_list):
            with cols[i % 5]:
                is_sel = gid in selected_ids
                if st.button(
                    f"{'✓ ' if is_sel else ''}{gname}",
                    key=f"g_{gid}",
                    type="primary" if is_sel else "secondary",
                ):
                    _toggle_genre(gid)
                    st.rerun()

        if selected_ids:
            st.markdown(
                f'<span class="liked-badge">{len(selected_ids)} genre{"s" if len(selected_ids) != 1 else ""} selected</span>',
                unsafe_allow_html=True,
            )
        st.markdown("---")
        col_l, col_c, col_r = st.columns([2, 1, 2])
        with col_c:
            if st.button("Continue \u2192", type="primary", key="continue_btn",
                         disabled=len(selected_ids) == 0):
                _auto_save()
                st.session_state["phase"] = "movies"
                st.session_state["movie_page"] = 1
                st.rerun()
        return

    # ==================================================================
    # PHASE 2 — Movie selection
    # ==================================================================
    st.markdown(_render_step_dots(2), unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">Mark movies you\'ve seen and liked \u2014 the more you pick, the better your recommendations.</p>',
        unsafe_allow_html=True,
    )

    c_back, c_refresh, c_info, _ = st.columns([0.8, 1, 1.5, 3])
    with c_back:
        if st.button("\u2190 Genres", key="back_btn", type="secondary"):
            st.session_state["phase"] = "genres"
            st.rerun()
    with c_refresh:
        if st.button("\u21bb Show me different movies", key="refresh_btn", type="secondary"):
            st.session_state["movie_page"] = st.session_state.get("movie_page", 1) + 1
            st.rerun()
    with c_info:
        pg = st.session_state.get("movie_page", 1)
        st.markdown(f'<span class="page-badge">Page {pg}</span>', unsafe_allow_html=True)

    st.markdown(
        f'<p class="section-label">Well-known {", ".join(selected_names)} movies \u2014 all decades</p>',
        unsafe_allow_html=True,
    )

    page = st.session_state.get("movie_page", 1)
    all_movies = _tmdb_mixed_era(list(selected_ids), page=page)
    rng = random.Random(hash(tuple(sorted(selected_ids))) + page)
    display_movies = list(all_movies)
    rng.shuffle(display_movies)
    display_movies = display_movies[:MOVIES_PER_PAGE]

    if not display_movies:
        st.markdown(
            '<div class="empty-state"><div class="icon">\U0001f3ac</div>'
            "No movies loaded. Make sure your <code>.env</code> has a valid "
            "<code>TMDB_API_KEY</code>, then reload.</div>",
            unsafe_allow_html=True,
        )
        if st.button("Reload", key="reload_btn"):
            _tmdb_mixed_era.clear()
            st.rerun()
    else:
        cols = st.columns(5)
        for i, m in enumerate(display_movies):
            with cols[i % 5]:
                liked = m.id in st.session_state["liked_tmdb_ids"]
                year_str = (m.release_date or "")[:4]
                meta = f"{year_str or '\u2014'}  \u00b7  \u2605 {m.vote_average:.1f}"
                if m.genre_names:
                    meta += f"  \u00b7  {' \u00b7 '.join(m.genre_names[:2])}"
                st.markdown(
                    _movie_card_html(m.poster_url, m.title, meta, liked, m.release_date),
                    unsafe_allow_html=True,
                )
                label = "\u2665 Liked" if liked else "\u2661 Like"
                if st.button(label, key=f"lk_{m.id}", type="primary" if liked else "secondary"):
                    _toggle_like(m)
                    _auto_save()
                    st.rerun()

    n_liked = len(st.session_state["liked_tmdb_ids"])
    if n_liked:
        st.markdown(
            f'<span class="liked-badge">\u2665 {n_liked} movie{"s" if n_liked != 1 else ""} liked</span>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ==================================================================
    # PHASE 3 — Recommendations (interactive)
    # ==================================================================
    st.markdown(_render_step_dots(3), unsafe_allow_html=True)
    st.markdown(
        '<p class="section-label">Get your personalised recommendations</p>',
        unsafe_allow_html=True,
    )

    col_slider, col_btn, col_refresh_recs, _ = st.columns([1.2, 1, 1, 1.5])
    with col_slider:
        top_k = st.slider("How many?", 5, 40, 20, key="top_k")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        get_recs = st.button("\u2728 Recommend", type="primary", key="get_recs")
    with col_refresh_recs:
        st.markdown("<br>", unsafe_allow_html=True)
        refresh_recs = st.button("\u21bb Refresh", type="secondary", key="refresh_recs",
                                 disabled=not st.session_state.get("rec_generated"))

    if get_recs or refresh_recs:
        with st.spinner("Crunching recommendations \u2026"):
            items = _generate_recs(top_k)
        st.session_state["rec_items"] = items
        st.session_state["rec_generated"] = True
        _auto_save()
        st.rerun()

    # --- Render stored recommendations with interactive buttons ---
    rec_items: list = st.session_state.get("rec_items", [])
    if st.session_state.get("rec_generated") and rec_items:
        st.markdown('<p class="section-label">Your picks</p>', unsafe_allow_html=True)

        n_dismissed = len(st.session_state.get("dismissed_titles", set()))
        seen_in_session = len(st.session_state.get("liked_tmdb_titles", []))
        if n_dismissed or seen_in_session:
            badges = ""
            if seen_in_session:
                badges += f'<span class="feedback-count fb-seen">\u2665 {seen_in_session} liked</span>'
            if n_dismissed:
                badges += f'<span class="feedback-count fb-skip">\u2718 {n_dismissed} dismissed</span>'
            st.markdown(badges, unsafe_allow_html=True)

        for rank_i, item in enumerate(rec_items, 1):
            st.markdown(
                _rec_card_html(
                    rank_i,
                    item.get("poster_url"),
                    item["display_title"],
                    item["meta"],
                    item.get("reason", ""),
                    item.get("genres", ""),
                ),
                unsafe_allow_html=True,
            )
            bc1, bc2, _ = st.columns([1, 1, 4])
            safe_key = re.sub(r"[^a-zA-Z0-9]", "_", item["title"])[:40]
            with bc1:
                if st.button(
                    "\u2665 Seen it \u2014 loved it",
                    key=f"seen_{safe_key}_{rank_i}",
                    type="primary",
                ):
                    _mark_seen(item["title"])
                    st.rerun()
            with bc2:
                if st.button(
                    "\u2718 Not for me",
                    key=f"skip_{safe_key}_{rank_i}",
                    type="secondary",
                ):
                    _mark_not_for_me(item["title"])
                    st.rerun()

        st.markdown("---")
        st.markdown(
            '<p style="color:#7b7f96;font-size:0.85rem;text-align:center;">'
            'Mark movies above, then hit <b>\u21bb Refresh</b> to get updated recommendations.</p>',
            unsafe_allow_html=True,
        )

    elif st.session_state.get("rec_generated") and not rec_items:
        st.markdown(
            '<div class="empty-state"><div class="icon">\U0001f50d</div>'
            "You've reviewed all recommendations! Hit <b>\u21bb Refresh</b> to get a new batch, "
            "or go back and like more movies.</div>",
            unsafe_allow_html=True,
        )

    # ==================================================================
    # Sidebar
    # ==================================================================
    with st.sidebar:
        username = st.session_state.get("username", "")
        if username:
            st.markdown(
                f'<p class="section-label" style="color:#a78bfa;">\U0001f464 {username.title()}</p>',
                unsafe_allow_html=True,
            )
            if st.button("Switch user", key="side_switch", type="secondary"):
                st.session_state["phase"] = "login"
                st.session_state["username"] = ""
                st.rerun()
            st.markdown("---")

        n_dis = len(st.session_state.get("dismissed_titles", set()))
        if n_dis:
            st.caption(f"{n_dis} dismissed movie{'s' if n_dis != 1 else ''}.")
            if st.button("Clear dismissed list", key="clear_dismissed", type="secondary"):
                st.session_state["dismissed_titles"] = set()
                _auto_save()
                st.rerun()
            st.markdown("---")

        st.markdown(
            '<p class="section-label" style="color:#a78bfa;">Advanced</p>',
            unsafe_allow_html=True,
        )
        st.caption("Add movies from our full catalog to refine your recommendations.")
        with st.expander("Pick from catalog"):
            if st.session_state.get("artifacts_loaded"):
                arts = _get_artifacts()
                catalog = arts.movies_df["title"].tolist()
                picked = st.multiselect(
                    "Movies you've seen & liked",
                    catalog,
                    default=st.session_state.get("liked_movielens_titles", []),
                    key="catalog_pick",
                )
                st.session_state["liked_movielens_titles"] = picked
            else:
                st.caption('Click **\u2728 Recommend** first to load the catalog.')


if __name__ == "__main__":
    main()
