"""
OptimaCV — Cron-Compatible Entry Point
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Usage:
  python run.py

Cron (every 4 hours):
  0 */4 * * * cd /path/to/job_scrapper && python run.py >> logs/cron.log 2>&1
"""

import asyncio
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import run_pipeline


def main():
    """Entry point — run the full OptimaCV pipeline."""
    print("\n🏁 OptimaCV Stealth Job Aggregator — Starting...\n")

    try:
        stats = asyncio.run(run_pipeline())
        print(f"\n✅ Pipeline complete. {stats.get('inserted', 0)} new jobs added.\n")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n⛔ Pipeline interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
