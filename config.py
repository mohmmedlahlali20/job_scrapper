"""
OptimaCV — Configuration & URL Builders
"""

import os
import random
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

# ─── Database ──────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASS", ""),
    "db": os.getenv("DB_NAME", "jobs"),
}

# ─── Gemini ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ─── Search Parameters ─────────────────────────────────────────────────────────
SEARCH_KEYWORDS = [
    "Python Developer",
    "Fullstack Developer",
    "Backend Engineer",
    "Data Engineer",
    "DevOps Engineer",
]

LOCATION = "Morocco"

# Maximum pages per keyword per source
MAX_PAGES_LINKEDIN = 4       # 4 pages × 25 = 100 jobs max
MAX_PAGES_INDEED = 5         # 5 pages × 10 = 50 jobs max
MAX_PAGES_LINKEDIN_POSTS = 3 # scroll 3 times for lazy loading

# ─── Stealth Parameters ───────────────────────────────────────────────────────
# Normal delay range (seconds)
JITTER_MIN = 3
JITTER_MAX = 8

# "Human reading" long pause (15% chance)
LONG_PAUSE_CHANCE = 0.15
LONG_PAUSE_MIN = 20
LONG_PAUSE_MAX = 35

# Screen resolutions to rotate per keyword batch
SCREEN_RESOLUTIONS = [
    (1920, 1080),
    (1366, 768),
    (1440, 900),
    (1536, 864),
    (1280, 720),
    (2560, 1440),
    (1600, 900),
    (1680, 1050),
]

# Domains considered "internal" (not external apply links)
INTERNAL_DOMAINS = [
    "linkedin.com",
    "www.linkedin.com",
    "indeed.com",
    "ma.indeed.com",
    "www.indeed.com",
]

# Max redirects to follow when resolving apply URLs
MAX_REDIRECT_DEPTH = 10

# ─── Job Freshness ─────────────────────────────────────────────────────────────
JOB_MAX_AGE_DAYS = 30

# ─── URL Builders ──────────────────────────────────────────────────────────────

def build_linkedin_search_url(keyword: str, start: int = 0) -> str:
    """LinkedIn public guest job search API."""
    kw = quote_plus(keyword)
    loc = quote_plus(LOCATION)
    return (
        f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        f"?keywords={kw}&location={loc}"
        f"&f_TPR=r2592000"  # last 30 days
        f"&sortBy=DD"       # sort by date
        f"&start={start}"
    )


def build_linkedin_posts_url(keyword: str) -> str:
    """LinkedIn content search for #hiring posts."""
    kw = quote_plus(f"#hiring {keyword}")
    return (
        f"https://www.linkedin.com/search/results/content/"
        f"?keywords={kw}&sortBy=%22date_posted%22"
    )


def build_indeed_search_url(keyword: str, start: int = 0) -> str:
    """Indeed Morocco public job search."""
    kw = quote_plus(keyword)
    return (
        f"https://ma.indeed.com/jobs"
        f"?q={kw}&l=Morocco&sort=date&start={start}"
    )


def get_random_jitter() -> float:
    """Return a human-like delay. 15% chance of a long 'reading' pause."""
    if random.random() < LONG_PAUSE_CHANCE:
        return random.uniform(LONG_PAUSE_MIN, LONG_PAUSE_MAX)
    return random.uniform(JITTER_MIN, JITTER_MAX)


def get_random_resolution() -> tuple[int, int]:
    """Pick a random screen resolution for Camoufox rotation."""
    return random.choice(SCREEN_RESOLUTIONS)
