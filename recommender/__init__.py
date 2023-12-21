from pathlib import Path
from dotenv import load_dotenv
import os

REPO_PATH = Path(__name__).parent.parent

assert load_dotenv(REPO_PATH / ".env"), f"Could not find .env at {REPO_PATH}"


# dot env fun

assert "CHROMA_PORT" in os.environ, "CHROMA_PORT must be set in .env"
CHROMA_PORT = os.environ["CHROMA_PORT"]

MIN_RATING_LEN = 5
MIN_SCORE = 0.2
MAX_RECOMENDATIOSN = 20
