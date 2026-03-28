"""
OptimaCV — Engine Orchestrator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pipeline: Scrape → Resolve → Immediate Row-by-Row Insert → Cleanup → Log
Designed to be cron-compatible (stateless, idempotent).
"""

import asyncio
import logging
import time
import hashlib
from datetime import datetime

from config import SEARCH_KEYWORDS
from models import RawJob, JobListing
from db import JobDatabase
from scrapers.linkedin import LinkedInScraper
from scrapers.linkedin_posts import LinkedInPostsScraper
from scrapers.indeed import IndeedScraper
from filters.gemini_filter import filter_jobs

import os

os.makedirs("logs", exist_ok=True)

# ─── Logging Setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-28s │ %(levelname)-5s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("logs/scraper.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("optimacv.engine")


async def run_pipeline() -> dict:
    """
    Main orchestrator pipeline.
    Returns a summary dict of the run stats.
    """
    start_time = time.time()
    logger.info("=" * 70)
    logger.info("🚀 OptimaCV Engine — Starting pipeline run")
    logger.info(f"📅 Timestamp: {datetime.now().isoformat()}")
    logger.info(f"🔑 Keywords: {SEARCH_KEYWORDS}")
    logger.info("=" * 70)

    # ── Initialize DB ────────────────────────────────────────────────────────
    db = JobDatabase()
    await db.connect()

    # ── Initialize Scrapers ──────────────────────────────────────────────────
    linkedin_scraper = LinkedInScraper()
    posts_scraper = LinkedInPostsScraper()
    indeed_scraper = IndeedScraper()

    all_raw_jobs: list[RawJob] = []
    stats = {
        "keywords_processed": 0,
        "raw_linkedin": 0,
        "raw_linkedin_posts": 0,
        "raw_indeed": 0,
        "total_raw": 0,
        "inserted": 0,
        "cleaned_up": 0,
        "duration_sec": 0,
    }

    # ── Scrape each keyword ──────────────────────────────────────────────────
    for keyword in SEARCH_KEYWORDS:
        logger.info(f"\n{'─' * 50}")
        logger.info(f"🔎 Processing keyword: '{keyword}'")
        logger.info(f"{'─' * 50}")

        async def handle_job(job: RawJob):
            if not job.apply_url:
                return

            job_hash = hashlib.sha256(job.apply_url.encode('utf-8')).hexdigest()
            job_data = {
                'title': job.job_title[:500],
                'company': job.company_name[:300],
                'location': job.location[:300],
                # The user mapped DB column "apply_url" to array key "link" in db.py
                'link': job.apply_url[:2000], 
                'source': job.source[:50],
                'job_hash': job_hash,
                'post_date': job.post_date.isoformat() if job.post_date else None,
                'description': job.description
            }
            
            # Save immediately to prevent data loss
            await db.save_job(job_data)
            stats["inserted"] += 1

        # Run all 3 scrapers concurrently for each keyword
        results = await asyncio.gather(
            _safe_scrape(linkedin_scraper, keyword, handle_job),
            _safe_scrape(posts_scraper, keyword, handle_job),
            _safe_scrape(indeed_scraper, keyword, handle_job),
            return_exceptions=True,
        )

        for i, result in enumerate(results):
            source = ["LinkedIn Jobs", "LinkedIn Posts", "Indeed"][i]
            if isinstance(result, Exception):
                logger.warning(f"⚠️ {source} scraper error: {result}")
            elif isinstance(result, list):
                logger.info(f"  {source}: {len(result)} raw jobs processed.")
                all_raw_jobs.extend(result)
                if i == 0:
                    stats["raw_linkedin"] += len(result)
                elif i == 1:
                    stats["raw_linkedin_posts"] += len(result)
                else:
                    stats["raw_indeed"] += len(result)

        stats["keywords_processed"] += 1

    stats["total_raw"] = len(all_raw_jobs)
    logger.info(f"\n📊 Total raw jobs scraped & saved: {stats['total_raw']}")

    # ── Cleanup old jobs ─────────────────────────────────────────────────────
    # User requested to keep all historical data:
    # cleaned = await db.cleanup_old_jobs()
    stats["cleaned_up"] = 0

    # ── Finalize ─────────────────────────────────────────────────────────────
    await db.close()

    elapsed = time.time() - start_time
    stats["duration_sec"] = round(elapsed, 1)

    _log_summary(stats)
    return stats


async def _safe_scrape(scraper, keyword: str, on_job_found=None) -> list[RawJob]:
    """Wrapper to catch and log scraper exceptions without killing the pipeline."""
    try:
        return await scraper.scrape(keyword, on_job_found)
    except Exception as e:
        logger.error(f"💥 {scraper.name} crashed on '{keyword}': {e}")
        return []


def _log_summary(stats: dict) -> None:
    """Print a final summary of the pipeline run."""
    logger.info("\n" + "═" * 70)
    logger.info("📋 PIPELINE RUN SUMMARY")
    logger.info("═" * 70)
    logger.info(f"  Keywords processed:    {stats['keywords_processed']}")
    logger.info(f"  Raw LinkedIn Jobs:     {stats['raw_linkedin']}")
    logger.info(f"  Raw LinkedIn Posts:    {stats['raw_linkedin_posts']}")
    logger.info(f"  Raw Indeed:            {stats['raw_indeed']}")
    logger.info(f"  Total Raw (Inserted):  {stats['total_raw']}")
    logger.info(f"  Insert Operations:     {stats['inserted']}")
    logger.info(f"  Old Jobs Cleaned:      {stats['cleaned_up']}")
    logger.info(f"  Duration:              {stats['duration_sec']}s")
    logger.info("═" * 70 + "\n")
