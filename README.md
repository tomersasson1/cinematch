# CineMatch — Movie & TV Recommendation System

[![Python 3.x](https://img.shields.io/badge/python-3.x-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Pandas](https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=white)](https://pandas.pydata.org/)

I built this movie and TV recommendation system in Python to combine several recommendation strategies into one hybrid approach. The goal was to create something that handles new users, learns from behavior, and uses content signals—all with a simple Streamlit UI so others can try it out locally.

---

## What I Implemented

- **Popularity baseline** — Counts ratings and averages so I can always recommend something reasonable, even for brand-new users.
- **Item–item collaborative filtering** — Builds a user–item matrix and computes similarity between movies based on how users rate them. If someone likes movie A, I recommend movies with similar rating patterns.
- **Content-based filtering** — Represents each movie by its genres and matches users to movies whose content features align with their preferences.
- **Hybrid recommender** — Blends these approaches with a weighted sum so different signals contribute to the final ranking.

The app lets users pick favorite genres and movies, then shows tailored recommendations with basic explanations. I kept the structure modular—core logic in `src/recommender`, UI in `app/`, and analysis in `notebooks/`—so it’s easy to extend or evaluate.

---

## Project Structure

```text
.
├── app/
│   └── streamlit_app.py
├── data/
│   ├── raw/                    # MovieLens ratings.csv, movies.csv
│   └── processed/              # Precomputed matrices
├── notebooks/
│   ├── 01_eda.ipynb
│   └── 02_model_prototyping.ipynb
├── src/
│   └── recommender/
│       ├── config.py
│       ├── data_loading.py
│       ├── preprocessing.py
│       ├── features.py
│       ├── evaluation.py
│       ├── interfaces.py
│       └── models/
│           ├── baseline.py
│           ├── collaborative.py
│           ├── content.py
│           └── hybrid.py
├── requirements.txt
└── README.md
```

---

## Dataset

I used the **MovieLens 25M** dataset. From the project root:

```bash
python scripts/download_movielens.py
```

That downloads the zip and copies `ratings.csv` and `movies.csv` into `data/raw/movielens/`. You can also download manually from [MovieLens](https://grouplens.org/datasets/movielens/) and place the CSVs there.

Expected columns:
- `ratings.csv`: userId, movieId, rating, timestamp
- `movies.csv`: movieId, title, genres

---

## Running It

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell

pip install -r requirements.txt
```

For faster startup after the first run:

```bash
python scripts/build_artifacts.py
```

Then start the app:

```bash
python run_app.py
```

Put a TMDB API key in `.env` (copy from `.env.example`) if you want "Most watched in your genres" and current movies. Get a free key from [TMDB API](https://www.themoviedb.org/settings/api).

---

## How the Recommender Works (High Level)

1. **Popularity baseline** — Each movie gets a score from its rating count and/or average. Used to always have reasonable fallback recommendations.
2. **Collaborative filtering** — User–item matrix (users × movies, entries = ratings). I compute item–item similarity from co-ratings. Liked movie A → recommend movies with similar rating patterns.
3. **Content-based** — Each movie is a genre vector. User preferences come from genres of liked movies. Recommendations are movies whose content is close to that preference vector.

The **hybrid** takes a weighted sum of these scores. I tuned the weights during prototyping and kept them config-driven.

---

## Possible Extensions

- Matrix factorization (e.g. `implicit`, `lightfm`) for better CF
- Improved evaluation metrics in `src/recommender/evaluation.py`
- Deploy to Streamlit Community Cloud — see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
