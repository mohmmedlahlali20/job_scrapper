"""
OptimaCV — Base Scraper
Abstract base class with stealth features:
  - Random jitter (normal 3-8s + 15% chance of 20-35s "reading" pause)
  - Camoufox screen resolution & UA rotation per keyword batch
  - Recursive redirect resolver → follows apply URLs to the REAL external domain
  - Login wall detection with retry
"""

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from urllib.parse import urlparse

import aiohttp

from config import (
    get_random_jitter,
    get_random_resolution,
    INTERNAL_DOMAINS,
    MAX_REDIRECT_DEPTH,
)
from models import RawJob

logger = logging.getLogger("optimacv.scraper")

# Common user agents for the redirect resolver's HTTP client
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


class BaseScraper(ABC):
    """Abstract base scraper with built-in stealth and redirect resolution."""

    name: str = "base"

    async def wait_jitter(self) -> None:
        """Human-like delay between requests."""
        delay = get_random_jitter()
        action = "🕰️ Long reading pause" if delay > 10 else "⏳ Jitter"
        logger.debug(f"{action}: {delay:.1f}s")
        await asyncio.sleep(delay)

    def get_stealth_params(self) -> dict:
        """
        Return StealthyFetcher params with a random screen resolution.
        Called once per keyword batch for rotation.
        """
        width, height = get_random_resolution()
        return {
            "headless": True,
            "block_images": True,
            "disable_resources": True,
            "screen_width": width,
            "screen_height": height,
        }

    @staticmethod
    def _is_internal_url(url: str) -> bool:
        """Check if URL belongs to an internal job board domain."""
        try:
            domain = urlparse(url).netloc.lower()
            return any(d in domain for d in INTERNAL_DOMAINS)
        except Exception:
            return True

    async def resolve_redirect(self, url: str) -> str:
        """
        Recursively follow redirects until we hit a non-LinkedIn/non-Indeed domain.
        Returns the final external URL, or the original if resolution fails.
        """
        if not url:
            return url

        try:
            headers = {"User-Agent": random.choice(_USER_AGENTS)}
            timeout = aiohttp.ClientTimeout(total=15)

            async with aiohttp.ClientSession(
                timeout=timeout,
                headers=headers,
            ) as session:
                current_url = url
                for _ in range(MAX_REDIRECT_DEPTH):
                    try:
                        async with session.head(
                            current_url,
                            allow_redirects=False,
                            ssl=False,
                        ) as resp:
                            # If redirect, follow it
                            if resp.status in (301, 302, 303, 307, 308):
                                next_url = resp.headers.get("Location", "")
                                if not next_url:
                                    break
                                # Handle relative redirects
                                if next_url.startswith("/"):
                                    parsed = urlparse(current_url)
                                    next_url = f"{parsed.scheme}://{parsed.netloc}{next_url}"
                                current_url = next_url
                                # If we've left the internal domain, we're done
                                if not self._is_internal_url(current_url):
                                    return current_url
                            else:
                                # No more redirects
                                break
                    except Exception:
                        # Try GET as fallback (some servers reject HEAD)
                        try:
                            async with session.get(
                                current_url,
                                allow_redirects=True,
                                ssl=False,
                            ) as resp:
                                current_url = str(resp.url)
                                if not self._is_internal_url(current_url):
                                    return current_url
                                break
                        except Exception:
                            break

                return current_url
        except Exception as e:
            logger.warning(f"⚠️ Redirect resolution failed for {url[:80]}: {e}")
            return url

    @staticmethod
    def detect_login_wall(html: str) -> bool:
        """Check if the page shows a login wall / auth gate."""
        wall_signals = [
            "authwall",
            "login-form",
            "sign in to continue",
            "join linkedin",
            "Sign in",
            "login-email",
        ]
        html_lower = html.lower() if html else ""
        return any(signal.lower() in html_lower for signal in wall_signals)

    @abstractmethod
    async def scrape(self, keyword: str, on_job_found=None) -> list[RawJob]:
        """Scrape jobs for a given keyword. Must be implemented by subclasses."""
        ...
