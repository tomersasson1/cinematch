"""
Download MovieLens dataset and extract ratings.csv + movies.csv to data/raw/movielens/.

Usage (from project root):
    python scripts/download_movielens.py [25m]

Uses MovieLens 25M (CSV). For smaller runs, you can manually download and use a subset.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

try:
    import urllib.request
except ImportError:
    urllib = None  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = PROJECT_ROOT / "data" / "raw"
MOVIELENS_DIR = DATA_RAW / "movielens"

URL_25M = "https://files.grouplens.org/datasets/movielens/ml-25m.zip"
SUBDIR_25M = "ml-25m"


def download_url(url: str, dest: Path) -> None:
    if urllib is None:
        raise RuntimeError("urllib not available")
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} ...")
    urllib.request.urlretrieve(url, dest)
    print(f"Saved to {dest}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Download MovieLens 25M data (CSV)")
    parser.add_argument("--force", action="store_true", help="Re-download even if zip exists")
    args = parser.parse_args()

    zip_path = DATA_RAW / "movielens-25m.zip"
    MOVIELENS_DIR.mkdir(parents=True, exist_ok=True)

    if not zip_path.exists() or args.force:
        download_url(URL_25M, zip_path)
    else:
        print(f"Using existing {zip_path}")

    extract_dir = DATA_RAW / SUBDIR_25M
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(DATA_RAW)

    for name in ["ratings.csv", "movies.csv"]:
        src = extract_dir / name
        if not src.exists():
            print(f"Missing {src}; aborting.")
            return 1
        shutil.copy2(src, MOVIELENS_DIR / name)
        print(f"Copied {name} -> {MOVIELENS_DIR / name}")

    print("Done. Run from project root: streamlit run app/streamlit_app.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
