from pathlib import Path
from dotenv import load_dotenv

REPO_PATH = Path(__name__).parent.parent

assert load_dotenv(REPO_PATH / ".env"), f"Could not find .env at {REPO_PATH}"
