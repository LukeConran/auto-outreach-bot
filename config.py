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
    "autonomous driving / autonomous vehicles",
    "occupancy networks",
    "bird's eye view (BEV) perception",
    "depth estimation",
    "SLAM",
    "edge computing / on-device perception",
    "medical imaging / 3D MRI",
    "imbalanced classification",
    "robot learning",
]

ARXIV_CATEGORIES = ["cs.CV", "cs.RO", "cs.LG"]

# --- Your positioning block: used verbatim by the draft agent ---
POSITIONING = """
I'm Luke Conran, an Honors CS undergrad and Data Science master's student at Texas A&M (both 4.00 GPA). My work centers on ML, 3D perception, and computer vision — at World Wide Technology I built a pipeline that turns 150M+ point LiDAR clouds into engineering-grade CAD with classical geometry and vision-language models; at the OptMAI Lab I research 3D MRI classification for Alzheimer's staging with contrastive learning, and I'm writing a thesis on MCI→AD conversion that maximizes partial AUC in the high-sensitivity region clinicians use.

I care as much about the surrounding pipeline and stakeholder problem as the model itself.
Portfolio: https://www.lukeconran.dev
GitHub: https://github.com/LukeConran
Ask: Summer 2027 ML eng / applied science internship (new-grad roles from 2028) — a brief chat about your team's work, or a pointer to open roles.
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
