"""
Precompute recommender artifacts so the Streamlit app loads in seconds.

Run from project root (with src on PYTHONPATH or from repo root):
    python scripts/build_artifacts.py

Then start the app; it will load from data/processed/artifacts.pkl instead of
rebuilding from MovieLens CSVs (much faster).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from recommender.interfaces import load_default_artifacts, save_artifacts, ARTIFACTS_CACHE_PATH


def main() -> int:
    print("Building artifacts from MovieLens data (this may take a minute)...")
    artifacts = load_default_artifacts(use_cache=False)
    save_artifacts(artifacts)
    print(f"Saved to {ARTIFACTS_CACHE_PATH}")
    print("Start the app with: python -m streamlit run app/streamlit_app.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
