"""
OptimaCV — Async MySQL Database Layer
Handles connection, logic, and insertion.
"""

import aiomysql
import logging
from datetime import date, timedelta
from typing import Optional

from config import DB_CONFIG, JOB_MAX_AGE_DAYS

logger = logging.getLogger("optimacv.db")

CREATE_TABLE_SQL = """
CREATE TABLE job_listings (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    title           VARCHAR(500)  NOT NULL,
    company         VARCHAR(300)  NOT NULL,
    location        VARCHAR(300)  NOT NULL,
    apply_url       VARCHAR(2000) NOT NULL,
    source          VARCHAR(50)   NOT NULL,
    job_hash        VARCHAR(64)   NOT NULL,
    post_date       DATE          NULL,
    description     TEXT          NULL,
    created_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_job_hash (job_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


class JobDatabase:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await aiomysql.create_pool(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            db=DB_CONFIG["db"],
            autocommit=True,
            charset="utf8mb4",
            minsize=1,
            maxsize=5,
        )
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Ensure the new schema is used.
                await cur.execute("DROP TABLE IF EXISTS job_listings;")
                await cur.execute(CREATE_TABLE_SQL)
                await conn.commit()
        logger.info("✅ Database logic initialized.")

    async def close(self):
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()

    async def save_job(self, job_data: dict):
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # صححنا 'link' لـ 'apply_url' هنا
                    sql = """REPLACE INTO job_listings 
                             (title, company, location, apply_url, source, job_hash, post_date, description) 
                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""

                    values = (
                        job_data["title"],
                        job_data["company"],
                        job_data["location"],
                        job_data[
                            "link"
                        ],  # هادا جاي من السكرابير سميتو link، غايتحط فـ apply_url
                        job_data["source"],
                        job_data["job_hash"],
                        job_data.get("post_date"),
                        job_data.get("description"),
                    )

                    await cur.execute(sql, values)
                    await conn.commit()

                    if cur.rowcount > 0:
                        print(f"✅ ✅ [DB SUCCESS] Saved: {job_data['title']}")
                        logger.info(f"Successfully saved job: {job_data['title']}")
                    else:
                        print(f"⚠️ [DB SKIP] Duplicate: {job_data['title']}")
        except Exception as e:
            print(f"❌ ❌ [DB FATAL ERROR]: {e}")

    async def cleanup_old_jobs(self) -> int:
        """Delete jobs older than JOB_MAX_AGE_DAYS. Returns count of deleted rows."""
        cutoff = (date.today() - timedelta(days=JOB_MAX_AGE_DAYS)).isoformat()
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "DELETE FROM job_listings WHERE post_date < %s", (cutoff,)
                    )
                    deleted = cur.rowcount
                    await conn.commit()
            return deleted
        except Exception as e:
            print(f"DB Cleanup Error: {e}")
            return 0
