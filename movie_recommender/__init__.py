from pathlib import Path
from dotenv import load_dotenv
import os

REPO_PATH = Path(__file__).parent.parent.absolute()

assert load_dotenv(REPO_PATH / ".env"), f"Could not find .env at {REPO_PATH}"


# dot env fun

assert "CHROMA_PORT" in os.environ, "CHROMA_PORT must be set in .env"
CHROMA_PORT = os.environ["CHROMA_PORT"]

assert "BackGroundTimeout" in os.environ, "BackGroundTimeout must be set in .env"
Back_Ground_Timeout = int(os.environ["BackGroundTimeout"])


assert (
    "RECOMMENDATIONS_CACHED_N_USERS" in os.environ
), "RECOMMENDATIONS_CACHED_N_USERS must be set in .env"
RECOMMENDATIONS_CACHED_N_USERS = int(os.environ["RECOMMENDATIONS_CACHED_N_USERS"])

assert (
    "RECOMMENDATIONS_CACHE_TIME" in os.environ
), "RECOMMENDATIONS_CACHE_TIME must be set in .env"
RECOMMENDATIONS_CACHE_TIME = int(os.environ["RECOMMENDATIONS_CACHE_TIME"])

MIN_RATING_LEN = 5
MIN_SCORE = 0.2
MAX_RECOMENDATIOSN = 20
