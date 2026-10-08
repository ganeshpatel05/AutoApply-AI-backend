"""AutoApply AI — Configuration Settings"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Project Root ──────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent

# Load environment variables from .env
load_dotenv(dotenv_path=BASE_DIR.parent / '.env')

# ── Ollama LLM ───────────────────────────────────────────────────
OLLAMA_MODEL      = os.getenv("OLLAMA_MODEL", "mistral")
OLLAMA_BASE_URL   = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

def _safe_int_env(key: str, default: int) -> int:
    val = os.getenv(key)
    if val is not None and val.strip().isdigit():
        return int(val.strip())
    return default

# ── Email (Gmail SMTP) ───────────────────────────────────────────
EMAIL_SENDER      = os.getenv("EMAIL_SENDER", "")
EMAIL_APP_PASSWORD= os.getenv("EMAIL_APP_PASSWORD", "")
SMTP_HOST         = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT         = _safe_int_env("EMAIL_SMTP_PORT", 587)

# ── Database ─────────────────────────────────────────────────────
db_env = os.getenv("DB_PATH", "").strip()
if db_env:
    DB_PATH = BASE_DIR / db_env
elif os.getenv("VERCEL"):
    DB_PATH = Path("/tmp/autoapply.db")
else:
    DB_PATH = BASE_DIR / "database" / "autoapply.db"

# ── Scraper ──────────────────────────────────────────────────────
SCRAPE_DELAY      = _safe_int_env("SCRAPE_DELAY_SECONDS", 2)
MAX_JOBS          = _safe_int_env("MAX_JOBS_PER_SEARCH", 20)

# ── Upload Paths ─────────────────────────────────────────────────
if os.getenv("VERCEL"):
    RESUME_UPLOAD_DIR = Path("/tmp/uploads/resumes")
    CL_UPLOAD_DIR     = Path("/tmp/uploads/cover_letters")
else:
    RESUME_UPLOAD_DIR = BASE_DIR / "uploads" / "resumes"
    CL_UPLOAD_DIR     = BASE_DIR / "uploads" / "cover_letters"


# ── Scraper Target URLs ───────────────────────────────────────────
SCRAPER_URLS = {
    "naukri": "https://www.naukri.com/{role}-jobs-in-{location}",
    "timesjobs": "https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords={role}&txtLocation={location}",
    "internshala": "https://internshala.com/jobs/{role}-jobs-in-{location}",
}

# ── ATS Scoring ───────────────────────────────────────────────────
ATS_HIGH_THRESHOLD   = 70   # Green badge ≥ 70%
ATS_MEDIUM_THRESHOLD = 50   # Yellow badge ≥ 50%
                             # Red badge   < 50%

# ── Performance Tuning ────────────────────────────────────────────
DB_WAL_MODE              = True
DB_CACHE_SIZE            = -64000    # 64MB page cache
DB_BUSY_TIMEOUT          = 10000     # 10 seconds
OLLAMA_CONNECT_TIMEOUT   = 5
OLLAMA_READ_TIMEOUT      = 60
MAX_COVER_LETTER_WORKERS = 3

# ── App Metadata ─────────────────────────────────────────────────
APP_NAME    = "AutoApply AI"
APP_VERSION = "1.0.0"
APP_ICON    = "🤖"
