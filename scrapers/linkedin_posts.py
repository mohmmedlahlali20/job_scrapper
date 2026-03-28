"""
OptimaCV — LinkedIn #Hiring Posts Scraper (via Google Dorking)
Uses Scrapy-style Selectors: .css('sel::text').get() and ::attr()
"""

import asyncio
import logging
from datetime import date
from urllib.parse import quote_plus

from scrapling.fetchers import AsyncStealthySession

from config import MAX_PAGES_LINKEDIN_POSTS
from models import RawJob
from scrapers.base import BaseScraper

logger = logging.getLogger("optimacv.linkedin_posts")


def _build_google_dork_url(keyword: str, start: int = 0) -> str:
    """Build Google search URL for LinkedIn #hiring posts."""
    query = quote_plus(f'site:linkedin.com/posts/ #hiring {keyword} Morocco')
    return f"https://www.google.com/search?q={query}&start={start}"


class LinkedInPostsScraper(BaseScraper):
    name = "linkedin_posts"

    async def scrape(self, keyword: str, on_job_found=None) -> list[RawJob]:
        """Scrape Google search results for LinkedIn #hiring posts."""
        jobs: list[RawJob] = []
        stealth = self.get_stealth_params()

        logger.info(
            f"🔍 LinkedIn Posts (Google Dork): '#hiring {keyword}' "
            f"(res: {stealth.get('screen_width')}x{stealth.get('screen_height')})"
        )

        try:
            async with AsyncStealthySession(
                headless=stealth.get("headless", True),
                block_images=False,
                disable_resources=False,
            ) as session:
                for page_idx in range(MAX_PAGES_LINKEDIN_POSTS):
                    start = page_idx * 10
                    url = _build_google_dork_url(keyword, start)

                    try:
                        page = await session.fetch(url)
                    except Exception as e:
                        logger.warning(f"⚠️ Google fetch failed (page {page_idx}): {e}")
                        await self.wait_jitter()
                        continue

                    try:
                        raw_html = str(page.body) if hasattr(page, "body") else str(page)
                    except Exception:
                        raw_html = str(page)
                    
                    if "captcha" in raw_html.lower() or "unusual traffic" in raw_html.lower():
                        logger.warning("🚫 Google CAPTCHA detected. Stopping.")
                        break

                    results = page.css("div.g")
                    if not results:
                        results = page.css("div.tF2Cxc")
                    if not results:
                        logger.info(f"  Page {page_idx}: 0 Google results.")
                        break

                    page_jobs = 0
                    for result in results:
                        try:
                            job = self._parse_google_result(result)
                            if job:
                                jobs.append(job)
                                page_jobs += 1
                                if on_job_found:
                                    await on_job_found(job)
                        except Exception as e:
                            logger.debug(f"  Result parse error: {e}")

                    logger.info(f"  Page {page_idx}: {page_jobs} posts extracted from Google.")

                    if page_idx < MAX_PAGES_LINKEDIN_POSTS - 1:
                        await self.wait_jitter()

        except Exception as e:
            logger.error(f"💥 LinkedIn Posts (Google) session error: {e}")

        logger.info(f"✅ LinkedIn Posts: {len(jobs)} raw jobs for '#hiring {keyword}'.")
        return jobs

    def _parse_google_result(self, result) -> RawJob | None:
        """Parse a Google search result pointing to a LinkedIn post."""
        
        # ── Get the LinkedIn post URL ───────────────────────────────────────
        post_url = ""
        for a_href in result.css("a::attr(href)").getall():
            if "linkedin.com/posts/" in a_href:
                post_url = a_href.strip()
                break

        if not post_url:
            return None

        # ── Title ───────────────────────────────────────────────────────────
        title_text = result.css("h3::text").get()
        title_text = title_text.strip() if title_text else ""

        # ── Snippet ─────────────────────────────────────────────────────────
        snippet = ""
        for sel in ["div.VwiC3b::text", "span.aCOpRe::text", "div.IsZvec::text"]:
            snip = result.css(sel).get()
            if snip:
                snippet = snip.strip()
                break

        if not snippet and not title_text:
            return None

        combined = (title_text + " " + snippet).lower()
        job_signals = [
            "hiring", "looking for", "job", "position",
            "apply", "role", "opportunity", "developer",
            "engineer", "recruiter", "join", "we're",
        ]
        if not any(signal in combined for signal in job_signals):
            return None

        # ── Company ─────────────────────────────────────────────────────────
        company = "Unknown"
        if " on LinkedIn" in title_text:
            company = title_text.split(" on LinkedIn")[0].strip()
        elif " - LinkedIn" in title_text:
            company = title_text.split(" - LinkedIn")[0].strip()
        elif "posted on" in title_text.lower():
            company = title_text.split("posted on")[0].strip()

        # ── Images for OCR ──────────────────────────────────────────────────
        image_urls: list[str] = []
        for src in result.css("img::attr(src)").getall():
            if src and src.startswith("http") and "google" not in src:
                image_urls.append(src.strip())

        return RawJob(
            job_title=f"[Post] {company}",
            company_name=company,
            location="Morocco",
            apply_url=post_url,
            post_date_raw="Recent",
            post_date=date.today(),
            description=f"{title_text}\n\n{snippet}"[:2000],
            image_urls=image_urls[:3],
            source="linkedin_posts",
        )
