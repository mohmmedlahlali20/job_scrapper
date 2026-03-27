"""
OptimaCV — Indeed Morocco Scraper
Uses Scrapy-style Selectors: .css('sel::text').get() and ::attr()
"""

import asyncio
import logging
import re
from datetime import date, timedelta

from scrapling.fetchers import AsyncStealthySession

from config import build_indeed_search_url, MAX_PAGES_INDEED
from models import RawJob
from scrapers.base import BaseScraper

logger = logging.getLogger("optimacv.indeed")


class IndeedScraper(BaseScraper):
    name = "indeed"

    async def scrape(self, keyword: str, on_job_found=None) -> list[RawJob]:
        """Scrape Indeed Morocco for job listings matching keyword."""
        jobs: list[RawJob] = []
        stealth = self.get_stealth_params()

        logger.info(
            f"🔍 Indeed: '{keyword}' "
            f"(res: {stealth.get('screen_width')}x{stealth.get('screen_height')})"
        )

        try:
            async with AsyncStealthySession(
                headless=stealth.get("headless", True),
                block_images=True,
                disable_resources=False,
                network_idle=True,
            ) as session:
                for page_idx in range(MAX_PAGES_INDEED):
                    start = page_idx * 10
                    url = build_indeed_search_url(keyword, start)

                    try:
                        page = await session.fetch(url)
                    except Exception as e:
                        logger.warning(f"⚠️ Indeed fetch failed (page {page_idx}): {e}")
                        await self.wait_jitter()
                        continue

                    try:
                        raw_html = str(page.body) if hasattr(page, "body") else str(page)
                    except Exception:
                        raw_html = str(page)

                    if "captcha" in raw_html.lower() or "cf-challenge" in raw_html.lower():
                        logger.warning(f"🚫 Cloudflare challenge on page {page_idx}. Stopping.")
                        break

                    cards = page.css(".job_seen_beacon")
                    if not cards:
                        cards = page.css("[data-jk]")
                    if not cards:
                        cards = page.css(".resultContent")
                    if not cards:
                        logger.info(f"  Page {page_idx}: 0 cards found.")
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

                    if page_idx < MAX_PAGES_INDEED - 1:
                        await self.wait_jitter()

        except Exception as e:
            logger.error(f"💥 Indeed session error: {e}")

        if jobs:
            logger.info(f"🔗 Resolving {len(jobs)} Indeed apply URLs...")
            for job in jobs:
                if job.apply_url and self._is_internal_url(job.apply_url):
                    job.apply_url = await self.resolve_redirect(job.apply_url)
                    await asyncio.sleep(0.5)
                if on_job_found:
                    await on_job_found(job)

        logger.info(f"✅ Indeed: {len(jobs)} raw jobs for '{keyword}'.")
        return jobs

    def _parse_card(self, card) -> RawJob | None:
        """Parse a single Indeed job card using ::text and ::attr() API."""

        # ── Title ───────────────────────────────────────────────────────────
        title = None
        # Try title attribute first
        title_attr = card.css("h2.jobTitle a::attr(title)").get()
        if title_attr:
            title = title_attr.strip()
        
        if not title:
            title_text = card.css("h2.jobTitle a::text").get()
            if title_text:
                title = title_text.strip()
                
        if not title:
            title_text = card.css("h2.jobTitle span::text").get()
            if title_text:
                title = title_text.strip()

        if not title:
            return None

        # ── Company ─────────────────────────────────────────────────────────
        company = card.css('[data-testid="company-name"]::text').get()
        if not company:
            company = card.css(".companyName::text").get()
        company = company.strip() if company else "Unknown"

        # ── Location ────────────────────────────────────────────────────────
        location = card.css('[data-testid="text-location"]::text').get()
        if not location:
            location = card.css(".companyLocation::text").get()
        location = location.strip() if location else "Morocco"

        # ── Date ────────────────────────────────────────────────────────────
        date_text = card.css(".date::text").get()
        if not date_text:
            date_text = card.css("span.date::text").get()
            
        date_text = date_text.strip() if date_text else ""
        post_date = self._parse_relative_date(date_text)

        # ── Apply URL ───────────────────────────────────────────────────────
        apply_url = ""
        href = card.css("h2.jobTitle a::attr(href)").get()
        
        if href:
            href = href.strip()
            if href.startswith("/"):
                apply_url = f"https://ma.indeed.com{href}"
            else:
                apply_url = href

        if not apply_url:
            for a_href in card.css("a::attr(href)").getall():
                if a_href and ("clk" in a_href or "jk=" in a_href):
                    a_href = a_href.strip()
                    if a_href.startswith("/"):
                        apply_url = f"https://ma.indeed.com{a_href}"
                    else:
                        apply_url = a_href
                    break

        if not apply_url:
            return None

        return RawJob(
            job_title=title,
            company_name=company,
            location=location,
            apply_url=apply_url,
            post_date_raw=date_text,
            post_date=post_date,
            source="indeed",
        )

    @staticmethod
    def _parse_relative_date(text: str) -> date | None:
        """Parse Indeed's relative date text."""
        if not text:
            return None

        text_lower = text.lower()
        today = date.today()

        if re.search(r"just posted|today|active today", text_lower):
            return today

        match = re.search(r"(\d+)\s*day", text_lower)
        if match:
            return today - timedelta(days=int(match.group(1)))

        if re.search(r"(\d+)\s*hour", text_lower):
            return today

        match = re.search(r"(\d+)\s*week", text_lower)
        if match:
            return today - timedelta(weeks=int(match.group(1)))

        match = re.search(r"(\d+)\s*month", text_lower)
        if match:
            return today - timedelta(days=int(match.group(1)) * 30)

        return None
