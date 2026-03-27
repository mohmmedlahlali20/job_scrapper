"""
OptimaCV — Gemini AI Semantic Filter + Multimodal OCR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Uses the new `google.genai` SDK (replaces deprecated google.generativeai).
Responsibilities:
  1. Date Filter:     Discard jobs older than 30 days
  2. Link Filter:     Discard internal (Easy Apply / linkedin / indeed) URLs
  3. Deduplication:   Same title+company → keep most recent
  4. Multimodal OCR:  If post has images, ask Gemini Vision to extract
                      contact emails / application instructions → description
  5. Fallback:        If Gemini fails → apply rule-based filtering
"""

import asyncio
import json
import logging
import re
from datetime import date, timedelta
from typing import Optional
from urllib.parse import urlparse

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, INTERNAL_DOMAINS, JOB_MAX_AGE_DAYS
from models import RawJob, JobListing

logger = logging.getLogger("optimacv.gemini")

# ─── Initialize Gemini Client ──────────────────────────────────────────────────
client = genai.Client(api_key=GEMINI_API_KEY)

MODEL = "gemini-2.0-flash"

# ─── Constants ──────────────────────────────────────────────────────────────────
TODAY = date.today()
CUTOFF_DATE = TODAY - timedelta(days=JOB_MAX_AGE_DAYS)

# ─── Prompts ────────────────────────────────────────────────────────────────────

FILTER_PROMPT_TEMPLATE = """You are an Elite Data Extraction Agent for OptimaCV, a Job Aggregator platform.

**TODAY'S DATE**: {today}
**CUTOFF DATE** (30 days ago): {cutoff}

You are given a JSON array of raw scraped job listings. Apply these STRICT filters:

1. **DATE FILTER**: If `post_date` is before {cutoff}, REMOVE the job entirely.
   - If `post_date` is null/empty, keep the job only if `post_date_raw` suggests it's recent.

2. **LINK FILTER**: Examine `apply_url`.
   - If the URL domain is linkedin.com, indeed.com, or any subdomain thereof → REMOVE.
   - If the URL contains "Easy Apply" indicators or is empty → REMOVE.
   - We ONLY want jobs whose `apply_url` leads to an EXTERNAL company career page.

3. **DEDUPLICATION**: If multiple jobs share the same `company_name` AND `job_title`, keep ONLY the most recent one.

4. **DATA CLEANUP**: For each surviving job, return a clean JSON object:
   - `job_title`: Clean title (remove "[Post]" prefixes)
   - `company_name`: Clean company name
   - `location`: City, Country format
   - `apply_url`: The external URL
   - `post_date`: ISO-8601 (YYYY-MM-DD)
   - `source`: Keep original source value
   - `description`: Keep if present, null otherwise

Return ONLY a valid JSON array. No markdown, no explanation, no code blocks.
If no jobs survive the filters, return an empty array: []

**RAW JOBS DATA:**
{jobs_json}
"""

OCR_PROMPT = """You are analyzing a job posting image for OptimaCV.

Extract ANY of the following if visible in the image:
1. **Contact email addresses** (e.g. hr@company.com, careers@company.com)
2. **Application instructions** (e.g. "Send CV to...", "Apply at...")
3. **Application URLs** (e.g. careers.company.com/apply)
4. **WhatsApp numbers** or phone numbers for applications

Return a JSON object:
{
  "emails": ["email1@example.com"],
  "urls": ["https://careers.example.com"],
  "instructions": "Any application instructions found",
  "phones": ["+212..."]
}

If nothing relevant is found, return: {"emails": [], "urls": [], "instructions": null, "phones": []}
Return ONLY valid JSON. No markdown, no explanation.
"""


# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

async def filter_jobs(raw_jobs: list[RawJob]) -> list[JobListing]:
    """
    Main entry point: filter raw jobs through Gemini AI.
    Falls back to rule-based filtering if Gemini fails.
    """
    if not raw_jobs:
        return []

    logger.info(f"🧠 Sending {len(raw_jobs)} raw jobs to Gemini for filtering...")

    # STEP 1: Process images via OCR (for linkedin_posts with images)
    await _enrich_with_ocr(raw_jobs)

    # STEP 2: Send to Gemini for semantic filtering
    try:
        filtered = await _gemini_filter(raw_jobs)
        logger.info(f"✅ Gemini returned {len(filtered)} filtered jobs.")
        return filtered
    except Exception as e:
        logger.warning(f"⚠️ Gemini filtering failed: {e}. Falling back to rule-based.")
        return _fallback_filter(raw_jobs)


# ═══════════════════════════════════════════════════════════════════════════════
#  GEMINI TEXT FILTERING
# ═══════════════════════════════════════════════════════════════════════════════

async def _gemini_filter(raw_jobs: list[RawJob]) -> list[JobListing]:
    """Send raw jobs to Gemini for AI-powered filtering and deduplication."""
    jobs_data = [j.to_dict() for j in raw_jobs]

    all_filtered: list[JobListing] = []
    chunk_size = 50

    for i in range(0, len(jobs_data), chunk_size):
        chunk = jobs_data[i : i + chunk_size]
        chunk_json = json.dumps(chunk, indent=2, ensure_ascii=False)

        prompt = FILTER_PROMPT_TEMPLATE.format(
            today=TODAY.isoformat(),
            cutoff=CUTOFF_DATE.isoformat(),
            jobs_json=chunk_json,
        )

        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )

            # Parse response
            text = response.text.strip()
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

            result = json.loads(text)

            if isinstance(result, list):
                for item in result:
                    try:
                        listing = JobListing.from_dict(item)
                        all_filtered.append(listing)
                    except Exception as e:
                        logger.debug(f"  Skipping malformed item: {e}")
            else:
                logger.warning("  Gemini returned non-array response.")

        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ Gemini JSON parse error on chunk {i}: {e}")
            chunk_raw = raw_jobs[i : i + chunk_size]
            all_filtered.extend(_fallback_filter(chunk_raw))

        except Exception as e:
            logger.warning(f"⚠️ Gemini API error on chunk {i}: {e}")
            chunk_raw = raw_jobs[i : i + chunk_size]
            all_filtered.extend(_fallback_filter(chunk_raw))

        await asyncio.sleep(1)

    return all_filtered


# ═══════════════════════════════════════════════════════════════════════════════
#  MULTIMODAL OCR (Image Analysis)
# ═══════════════════════════════════════════════════════════════════════════════

async def _enrich_with_ocr(raw_jobs: list[RawJob]) -> None:
    """
    For jobs with image URLs, send to Gemini Vision to extract
    contact emails, application URLs, or instructions.
    """
    jobs_with_images = [j for j in raw_jobs if j.image_urls]

    if not jobs_with_images:
        return

    logger.info(f"🔎 Running OCR on {len(jobs_with_images)} jobs with images...")

    for job in jobs_with_images:
        for img_url in job.image_urls[:2]:
            try:
                ocr_result = await _ocr_image(img_url)
                if ocr_result:
                    _apply_ocr_result(job, ocr_result)
            except Exception as e:
                logger.debug(f"  OCR failed for {img_url[:60]}: {e}")
            await asyncio.sleep(0.5)


async def _ocr_image(image_url: str) -> Optional[dict]:
    """Send an image URL to Gemini Vision for OCR extraction."""
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL,
            contents=[OCR_PROMPT, image_url],
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )

        text = response.text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        return json.loads(text)

    except Exception as e:
        logger.debug(f"  Vision OCR error: {e}")
        return None


def _apply_ocr_result(job: RawJob, ocr: dict) -> None:
    """Merge OCR-extracted data into the job's description field."""
    parts: list[str] = []

    if job.description:
        parts.append(job.description)

    emails = ocr.get("emails", [])
    if emails:
        parts.append(f"📧 Contact: {', '.join(emails)}")

    urls = ocr.get("urls", [])
    if urls:
        parts.append(f"🔗 Apply: {', '.join(urls)}")
        if not job.apply_url or _is_internal(job.apply_url):
            for u in urls:
                if not _is_internal(u):
                    job.apply_url = u
                    break

    instructions = ocr.get("instructions")
    if instructions:
        parts.append(f"📋 {instructions}")

    phones = ocr.get("phones", [])
    if phones:
        parts.append(f"📱 Phone: {', '.join(phones)}")

    if len(parts) > (1 if job.description else 0):
        job.description = "\n".join(parts)


# ═══════════════════════════════════════════════════════════════════════════════
#  FALLBACK RULE-BASED FILTER
# ═══════════════════════════════════════════════════════════════════════════════

def _fallback_filter(raw_jobs: list[RawJob]) -> list[JobListing]:
    """Rule-based fallback when Gemini is unavailable."""
    logger.info("📐 Applying rule-based fallback filter...")
    seen: dict[str, JobListing] = {}

    for job in raw_jobs:
        # Date filter
        if job.post_date and job.post_date < CUTOFF_DATE:
            continue

        # Link filter — must be external
        if not job.apply_url or _is_internal(job.apply_url):
            continue

        listing = JobListing(
            job_title=job.job_title.replace("[Post] ", ""),
            company_name=job.company_name,
            location=job.location,
            apply_url=job.apply_url,
            post_date=job.post_date or TODAY,
            source=job.source,
            description=job.description,
        )

        # Dedup — keep most recent per title+company
        key = f"{listing.job_title.lower()}|{listing.company_name.lower()}"
        existing = seen.get(key)
        if existing:
            if listing.post_date >= existing.post_date:
                seen[key] = listing
        else:
            seen[key] = listing

    filtered = list(seen.values())
    logger.info(f"📐 Fallback filter: {len(filtered)} jobs survived.")
    return filtered


def _is_internal(url: str) -> bool:
    """Check if URL is an internal job board link."""
    try:
        domain = urlparse(url).netloc.lower()
        return any(d in domain for d in INTERNAL_DOMAINS)
    except Exception:
        return True
