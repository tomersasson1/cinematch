### Movie & TV Recommendation System

[![Python 3.x](https://img.shields.io/badge/python-3.x-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Pandas](https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=white)](https://pandas.pydata.org/)

This is a **portfolio-grade movie/TV recommendation system** built in Python.  
It focuses on **clean code structure**, **explainable models**, and a **simple local UI** so you can both learn and demonstrate practical data science skills.

#### Main features
- **Multiple recommendation strategies**
  - Popularity-based baseline.
  - Item–item collaborative filtering.
  - Content-based filtering using genres.
  - A simple hybrid that combines different signals.
- **Local UI with Streamlit**
  - Let a user pick favorite genres and movies.
  - Show tailored recommendations with basic explanations.
- **Reproducible workflow**
  - Clear project structure (`src/`, `app/`, `data/`, `notebooks/`).
  - Config-driven paths and parameters.

---

### 1. Project structure

```text
.
├── app/
│   └── streamlit_app.py        # Streamlit UI entrypoint
├── data/
│   ├── raw/                    # Raw MovieLens data (ratings.csv, movies.csv, …)
│   └── processed/              # Preprocessed data / matrices
├── notebooks/
│   ├── 01_eda.ipynb            # Exploratory data analysis
│   └── 02_model_prototyping.ipynb
├── src/
│   └── recommender/
│       ├── __init__.py
│       ├── config.py
│       ├── data_loading.py
│       ├── preprocessing.py
│       ├── features.py
│       ├── evaluation.py
│       ├── interfaces.py
│       └── models/
│           ├── __init__.py
│           ├── baseline.py
│           ├── collaborative.py
│           ├── content.py
│           └── hybrid.py
├── requirements.txt
└── README.md
```

This structure separates:
- **Core recommendation logic** (`src/recommender`) from
- **User interface** (`app/`) and
- **Experiments / analysis** (`notebooks/`).

---

### 2. Dataset

This project uses the **MovieLens 25M** dataset (CSV). Easiest way:

From the project root:

```bash
python scripts/download_movielens.py
```

This downloads the zip, extracts it, and copies `ratings.csv` and `movies.csv` into `data/raw/movielens/`. Alternatively, download from [MovieLens](https://grouplens.org/datasets/movielens/) and place the CSV files under `data/raw/movielens/`.

Expected columns:
- `ratings.csv`: `userId`, `movieId`, `rating`, `timestamp`
- `movies.csv`: `movieId`, `title`, `genres`

---

### 3. Environment setup

1. **Create and activate a virtual environment** (recommended):

```bash
python -m venv .venv
# On Windows (PowerShell)
.venv\\Scripts\\Activate.ps1
```

2. **Install dependencies**:

```bash
pip install -r requirements.txt
```

3. **Faster startup (optional)**  
   The first time you run the app it builds the recommendation engine from scratch (can take a minute). To make later starts fast, run once:

   ```bash
   python scripts/build_artifacts.py
   ```
   This saves precomputed data to `data/processed/artifacts.pkl`; the app will load from that file next time.

4. **Run the Streamlit app** (from project root):

```bash
python run_app.py
```
Put your TMDB API key in a `.env` file (copy from `.env.example`) so "Most watched in your genres" shows movies.

Using `python -m streamlit` ensures the correct environment’s Streamlit is used.

5. **Up-to-date movies (optional)**  
   The app can show **popular** and **in theatres** movies from [The Movie Database (TMDB)](https://www.themoviedb.org/). Get a free API key from [TMDB API](https://www.themoviedb.org/settings/api), then set:

   ```bash
   set TMDB_API_KEY=your_key_here
   ```
   (PowerShell). On Linux/macOS: `export TMDB_API_KEY=your_key_here`. The homepage will then display current movies alongside your personalized recommendations.

---

### 4. How the recommender works (high level)

At a high level, the system combines three ideas:

1. **Popularity baseline**
   - Count how many ratings each movie has and/or its average rating.
   - Use this to always be able to recommend *something reasonable*, even for brand new users.

2. **Collaborative filtering (CF)**
   - Build a large **user–item matrix** (rows are users, columns are movies, entries are ratings or implicit likes).
   - Compute similarity between movies based on how users rate them (item–item CF).
   - If you like movie A, recommend movies that have similar rating patterns to A.

3. **Content-based filtering**
   - Represent each movie by its **genres** (and optionally year or other metadata).
   - Represent the user’s preferences as a combination of the genres / movies they like.
   - Recommend movies whose content features are close to the user’s preference vector.

The **hybrid recommender** blends these pieces by taking a weighted sum of different scores.

---

### 5. Learning goals

This project is designed to teach you:
- How to **structure a real-world data science project**.
- How to build different types of **recommender systems**:
  - Popularity-based.
  - Collaborative filtering.
  - Content-based.
  - Hybrid.
- How to expose your model via a **simple interactive UI** (Streamlit).
- How to write **clean, well-organized Python code** with configuration, modules, and type hints.

---

### 6. Next steps in this repo

- **Deploy:** See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for temporary sharing (e.g. Cloudflare Tunnel) and portfolio hosting (e.g. Streamlit Community Cloud).

As you work through the project, you can:
- Explore the data and models in `notebooks/`.
- Improve evaluation metrics in `src/recommender/evaluation.py`.
- Add more advanced models (e.g. matrix factorization using `implicit` or `lightfm`).
- Polish the UI in `app/streamlit_app.py` to make it more “product-like” for your portfolio.

