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
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")  # optional, recommended for rate limits
SEMANTIC_SCHOLAR_API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")  # optional, recommended for rate limits
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
    "contrastive learning applications",
    "CNNs",
]

# Soft-exclude in scoring (not hard-dropped at discovery): LLM tuning / RAG-only work.
SOFT_EXCLUDE_TOPICS = [
    "LLM fine-tuning / instruction tuning as the primary contribution",
    "RAG / retrieval-augmented generation systems",
]

ARXIV_CATEGORIES = ["cs.CV", "cs.RO", "cs.LG"]

# --- Your positioning block: used verbatim by the draft agent ---
POSITIONING = """
I'm Luke Conran, an Honors CS undergrad and Data Science master's student at Texas A&M (both 4.00 GPA). My work centers on ML, 3D perception, and computer vision — at World Wide Technology I built a pipeline that turns 150M+ point LiDAR clouds into engineering-grade CAD with classical geometry and vision-language models; at the OptMAI Lab I research 3D MRI classification for Alzheimer's staging with contrastive learning, and I'm writing a thesis on MCI→AD conversion that maximizes partial AUC in the high-sensitivity region clinicians use.

I care as much about the surrounding pipeline and stakeholder problem as the model itself. Raised in St. Louis; always happy to connect over shared TAMU or St. Louis roots.
Portfolio: https://www.lukeconran.dev
GitHub: https://github.com/LukeConran
Ask: 15–20 minutes to hear about your career path and recent work — not a referral request and not a job pitch.
""".strip()

# --- Target companies (US industry). Append a dict to extend; matching is in industry.py. ---
# needles: affiliation / org-name substrings (normalized). domains: email domains.
COMPANY_ALLOWLIST = [
    {"name": "Uber", "needles": ["uber atg", "uber advanced technologies", "uber"], "domains": ["uber.com"]},
    {"name": "Waymo", "needles": ["waymo"], "domains": ["waymo.com"]},
    {"name": "DoorDash", "needles": ["doordash", "door dash"], "domains": ["doordash.com"]},
    {"name": "Lyft", "needles": ["lyft level 5", "lyft"], "domains": ["lyft.com"]},
    {"name": "Trimble", "needles": ["trimble"], "domains": ["trimble.com"]},
    {"name": "Zoox", "needles": ["zoox"], "domains": ["zoox.com"]},
    {"name": "General Motors", "needles": ["general motors"], "domains": ["gm.com"]},
    {"name": "Cruise", "needles": ["gm cruise", "cruise llc", "getcruise", "cruise"], "domains": ["getcruise.com", "cruise.com"]},
    {"name": "Two Sigma", "needles": ["two sigma", "twosigma"], "domains": ["twosigma.com"]},
    {"name": "Google", "needles": ["google research", "google brain", "google"], "domains": ["google.com"]},
    {"name": "Apple", "needles": ["apple"], "domains": ["apple.com"]},
    {"name": "Netflix", "needles": ["netflix"], "domains": ["netflix.com"]},
    {"name": "Amazon", "needles": ["amazon web services", "amazon", "aws"], "domains": ["amazon.com", "aws.com"]},
    {"name": "Microsoft", "needles": ["microsoft research", "microsoft"], "domains": ["microsoft.com"]},
    {"name": "NVIDIA", "needles": ["nvidia"], "domains": ["nvidia.com"]},
    {"name": "SpaceX", "needles": ["spacex", "space x"], "domains": ["spacex.com"]},
    {"name": "Tesla", "needles": ["tesla"], "domains": ["tesla.com"]},
    {"name": "Neuralink", "needles": ["neuralink"], "domains": ["neuralink.com"]},
    {"name": "Meta", "needles": ["meta platforms", "meta ai", "facebook ai research", "facebook", "meta"], "domains": ["meta.com", "fb.com"]},
    {"name": "OpenAI", "needles": ["openai"], "domains": ["openai.com"]},
    {"name": "Aurora", "needles": ["aurora innovation", "aurora.tech"], "domains": ["aurora.tech"]},
    {"name": "Motional", "needles": ["motional"], "domains": ["motional.com"]},
    {"name": "Plus.ai", "needles": ["plus.ai", "plus ai", "plusai"], "domains": ["plus.ai"]},
    {"name": "Rivian", "needles": ["rivian"], "domains": ["rivian.com"]},
    {"name": "Ford", "needles": ["ford motor", "ford"], "domains": ["ford.com"]},
    {"name": "Toyota Research", "needles": ["toyota research institute", "toyota research"], "domains": ["tri.global", "toyota.com"]},
    {"name": "Intel", "needles": ["intel labs", "intel"], "domains": ["intel.com"]},
    {"name": "Qualcomm", "needles": ["qualcomm"], "domains": ["qualcomm.com"]},
    {"name": "Scale AI", "needles": ["scale ai", "scale.ai"], "domains": ["scale.com", "scale.ai"]},
    {"name": "Anduril", "needles": ["anduril"], "domains": ["anduril.com"]},
]

# Default discovery path is US industry teams. Set to "academic" for the old arXiv-only path.
_DISCOVER_MODE = os.environ.get("DISCOVER_MODE", "industry").strip().lower()
DISCOVER_MODE = _DISCOVER_MODE if _DISCOVER_MODE in ("industry", "academic") else "industry"

# Keep candidates whose affiliation/email/company presence indicates US industry employment.
US_ONLY = True

# --- Guardrails ---
DAILY_CAP = int(os.environ.get("DAILY_CAP", "10"))
RELEVANCE_THRESHOLD = int(os.environ.get("RELEVANCE_THRESHOLD", "60"))  # 0-100, Grok score cutoff
FOLLOWUP_BUSINESS_DAYS = 6

# --- Rate limiting / caching ---
REQUEST_TIMEOUT_SECONDS = 20
CACHE_DIR = ROOT_DIR / ".cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL_SECONDS = 60 * 60 * 24  # 1 day
