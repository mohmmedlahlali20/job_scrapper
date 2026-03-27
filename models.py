"""
OptimaCV — Data Models
"""

from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Optional
import json


@dataclass
class RawJob:
    """A raw job scraped before filtering."""
    job_title: str
    company_name: str
    location: str
    apply_url: str
    post_date_raw: str = ""
    post_date: Optional[date] = None
    description: Optional[str] = None
    image_urls: list[str] = field(default_factory=list)
    source: str = ""  # "linkedin" | "linkedin_posts" | "indeed"

    def to_dict(self) -> dict:
        d = asdict(self)
        if d["post_date"]:
            d["post_date"] = d["post_date"].isoformat()
        return d


@dataclass
class JobListing:
    """A filtered, validated job ready for DB insertion."""
    job_title: str
    company_name: str
    location: str
    apply_url: str
    post_date: date
    source: str
    description: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "job_title": self.job_title,
            "company_name": self.company_name,
            "location": self.location,
            "apply_url": self.apply_url,
            "post_date": self.post_date.isoformat(),
            "source": self.source,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobListing":
        pd = data.get("post_date")
        if isinstance(pd, str):
            pd = date.fromisoformat(pd)
        return cls(
            job_title=data.get("job_title", ""),
            company_name=data.get("company_name", ""),
            location=data.get("location", ""),
            apply_url=data.get("apply_url", ""),
            post_date=pd or date.today(),
            source=data.get("source", ""),
            description=data.get("description"),
        )
