"""
OptimaCV — LinkedIn Public Guest Job Listings Scraper
Uses Scrapy-style Selectors: .css('sel::text').get() and ::attr()
"""

import asyncio
import logging
from datetime import date

from scrapling.fetchers import AsyncStealthySession

from config import (
    build_linkedin_search_url,
    MAX_PAGES_LINKEDIN,
)
from models import RawJob
from scrapers.base import BaseScraper

logger = logging.getLogger("optimacv.linkedin")


class LinkedInScraper(BaseScraper):
    name = "linkedin"

    async def scrape(self, keyword: str, on_job_found=None) -> list[RawJob]:
        """Scrape LinkedIn guest API for job listings matching keyword."""
        jobs: list[RawJob] = []
        stealth = self.get_stealth_params()

        logger.info(
            f"🔍 LinkedIn Jobs: '{keyword}' "
            f"(res: {stealth.get('screen_width')}x{stealth.get('screen_height')})"
        )

        try:
            async with AsyncStealthySession(
                headless=stealth.get("headless", True),
                block_images=True,
                disable_resources=True,
            ) as session:
                for page_idx in range(MAX_PAGES_LINKEDIN):
                    start = page_idx * 25
                    url = build_linkedin_search_url(keyword, start)

                    try:
                        page = await session.fetch(url)
                    except Exception as e:
                        logger.warning(f"⚠️ Fetch failed (page {page_idx}): {e}")
                        await self.wait_jitter()
                        continue

                    # Debug HTML
                    try:
                        raw_html = str(page.body) if hasattr(page, "body") else str(page)
                    except Exception:
                        raw_html = str(page)

                    if self.detect_login_wall(raw_html):
                        logger.warning("🚫 Login wall detected, stopping.")
                        break

                    # Parse job cards
                    cards = page.css("li")
                    if not cards:
                        logger.info(f"  Page {page_idx}: 0 <li> found.")
                        break

                    page_jobs = 0
                    for card in cards:
                        try:
                            job = self._parse_card(card)
                            if job:
                                jobs.append(job)
                                page_jobs += 1
                        except Exception as e:
                            logger.debug(f"  Card parse error: {e}")

                    logger.info(f"  Page {page_idx}: {page_jobs} jobs parsed.")

                    if page_idx < MAX_PAGES_LINKEDIN - 1:
                        await self.wait_jitter()

        except Exception as e:
            logger.error(f"💥 LinkedIn session error: {e}")

        # Resolve redirects
        if jobs:
            logger.info(f"🔗 Resolving {len(jobs)} apply URLs...")
            for job in jobs:
                if job.apply_url and self._is_internal_url(job.apply_url):
                    job.apply_url = await self.resolve_redirect(job.apply_url)
                    await asyncio.sleep(0.5)
                if on_job_found:
                    await on_job_found(job)

        logger.info(f"✅ LinkedIn Jobs: {len(jobs)} raw jobs for '{keyword}'.")
        return jobs

    def _parse_card(self, card) -> RawJob | None:
        """Parse a single LinkedIn guest API job card using ::text and ::attr()."""
        
        # ── Title ───────────────────────────────────────────────────────────
        title = card.css(".base-search-card__title::text").get()
        if not title:
            title = card.css("h3::text").get()
        if not title:
            return None
        title = title.strip()

        # ── Company ─────────────────────────────────────────────────────────
        company = card.css(".base-search-card__subtitle a::text").get()
        if not company:
            company = card.css("h4::text").get()
        
        company = company.strip() if company else "Unknown"

        # ── Location ────────────────────────────────────────────────────────
        location = card.css(".job-search-card__location::text").get()
        location = location.strip() if location else "Morocco"

        # ── Date ────────────────────────────────────────────────────────────
        post_date_raw = ""
        post_date = None
        
        # Try datetime attribute on time tag
        dt_attr = card.css("time::attr(datetime)").get()
        if dt_attr:
            dt_attr = dt_attr.strip()
            try:
                post_date = date.fromisoformat(dt_attr[:10])
                post_date_raw = dt_attr
            except Exception:
                pass

        if not post_date:
            date_text = card.css("time::text").get()
            if date_text:
                post_date_raw = date_text.strip()
        
        # Fallback listdate
        if not post_date:
            dt_attr = card.css(".job-search-card__listdate::attr(datetime)").get()
            if dt_attr:
                dt_attr = dt_attr.strip()
                try:
                    post_date = date.fromisoformat(dt_attr[:10])
                    post_date_raw = dt_attr
                except Exception:
                    pass

        # ── Apply URL ───────────────────────────────────────────────────────
        apply_url = card.css("a.base-card__full-link::attr(href)").get()
        
        if not apply_url:
            # Check all links
            for a_href in card.css("a::attr(href)").getall():
                if "/jobs/view/" in a_href or "/jobs/" in a_href:
                    apply_url = a_href
                    break
        
        if apply_url:
            apply_url = apply_url.strip()
        else:
            return None

        return RawJob(
            job_title=title,
            company_name=company,
            location=location,
            apply_url=apply_url,
            post_date_raw=post_date_raw,
            post_date=post_date,
            source="linkedin",
        )
