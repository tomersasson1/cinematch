# Architecture overview

## Data flow

1. **Raw data**  
   MovieLens `ratings.csv` and `movies.csv` live under `data/raw/movielens/`.

2. **Preprocessing**  
   `data_loading` reads CSVs; `preprocessing` filters inactive users and rare items, builds user/item ID ↔ index mappings, and a sparse user–item matrix (implicit: rating ≥ 4 → 1, else 0).

3. **Models**  
   - **Baseline**: popularity (count × avg_rating) with optional genre filter.  
   - **Collaborative**: item–item cosine similarity on the user–item matrix; recommend items similar to the user’s liked items.  
   - **Content**: genre multi-hot features; user vector from preferred genres + average of liked movies; cosine similarity to movie vectors.  
   - **Hybrid**: min–max normalize scores from each model and take a weighted sum (default 0.2 baseline, 0.5 collaborative, 0.3 content).

4. **UI**  
   Streamlit calls `interfaces.load_default_artifacts()` (cached) and `get_recommendations_for_user_preferences(artifacts, genres, liked_movie_ids, top_k)`. Results are shown as a table with title, genres, score, and reason.

## Design choices

- **Single entrypoint for the app**: `interfaces` so the UI stays thin and the same logic can be tested or reused elsewhere.
- **Config in one place**: `config.py` for paths and constants (min ratings, like threshold).
- **Cold start**: If the user selects no movies, collaborative has nothing to work with; the hybrid still uses baseline + content (genre-only preferences).

## Portfolio summary (for CV/LinkedIn)

- Built a **movie recommendation system** with popularity baseline, **item–item collaborative filtering**, **content-based** (genre) filtering, and a **hybrid** combiner.
- Implemented **offline evaluation** (Precision@K, Recall@K, AP@K) and exploratory notebooks on MovieLens data.
- Delivered a **Streamlit UI** for local, interactive recommendations from user-selected genres and liked movies.
- Structured the project with clear separation between data loading, preprocessing, models, and UI, using type hints and docstrings.
