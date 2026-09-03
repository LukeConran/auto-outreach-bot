"""Central configuration: interests, positioning, caps, thresholds, and API keys.

All secrets come from environment variables (.env), never hardcoded.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).parent
PENDING_DIR = ROOT_DIR / "pending"
HISTORY_DIR = ROOT_DIR / "history"
HISTORY_CSV = HISTORY_DIR / "contacts.csv"

for d in (PENDING_DIR, HISTORY_DIR):
    d.mkdir(exist_ok=True)

# --- API keys (read from .env; empty string if unset so imports never crash) ---
XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
SEMANTIC_SCHOLAR_API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")  # optional, higher rate limit
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")

# --- Grok / xAI model selection ---
XAI_BASE_URL = "https://api.x.ai/v1"
XAI_REASONING_MODEL = os.environ.get("XAI_REASONING_MODEL", "grok-4")  # scoring, hooks, drafts
XAI_FAST_MODEL = os.environ.get("XAI_FAST_MODEL", "grok-code-fast-1")  # cheap query expansion

# --- Your search domains / interests ---
INTERESTS = [
    "3D perception",
    "computer vision",
    "occupancy networks",
    "bird's eye view (BEV) perception",
    "NeRF",
    "depth estimation",
    "SLAM",
    "robot learning",
]

ARXIV_CATEGORIES = ["cs.CV", "cs.RO", "cs.LG"]

# --- Your positioning block: used verbatim by the draft agent ---
POSITIONING = """
I'm a student/engineer interested in 3D perception and computer vision for robotics.
GitHub: https://github.com/YOUR_USERNAME
Resume: https://YOUR_RESUME_LINK
Ask: a 15-minute call to learn about your work, or a referral/pointer to open roles.
""".strip()

# --- Guardrails ---
DAILY_CAP = int(os.environ.get("DAILY_CAP", "10"))
RELEVANCE_THRESHOLD = int(os.environ.get("RELEVANCE_THRESHOLD", "60"))  # 0-100, Grok score cutoff
FOLLOWUP_BUSINESS_DAYS = 6

# --- Rate limiting / caching ---
REQUEST_TIMEOUT_SECONDS = 20
CACHE_DIR = ROOT_DIR / ".cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL_SECONDS = 60 * 60 * 24  # 1 day
