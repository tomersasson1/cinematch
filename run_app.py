"""
Run the Streamlit app with TMDB_API_KEY loaded from .env (if present).

Usage from project root:
    python run_app.py

Create a file named .env in the project root with:
    TMDB_API_KEY=your_key_here
"""
import os
import sys
from pathlib import Path

# Project root = parent of this script
ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

# Load .env if it exists (KEY=value, one per line)
env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key:
                os.environ[key] = value

# Ensure src is on path for recommender package
sys.path.insert(0, str(ROOT / "src"))

# Run Streamlit
from streamlit.web import cli as stcli

sys.argv = ["streamlit", "run", str(ROOT / "app" / "streamlit_app.py")]
stcli.main()
