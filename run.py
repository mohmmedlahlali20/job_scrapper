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

import argparse

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import run_pipeline

async def run_continuously(interval_hours: int):
    """Run pipeline continuously every X hours."""
    print(f"\n🔄 OptimaCV Scheduler started. Running every {interval_hours} hours.\n")
    while True:
        try:
            stats = await run_pipeline()
            print(f"\n✅ Pipeline run complete. {stats.get('inserted', 0)} new jobs added.\n")
        except Exception as e:
            print(f"\n💥 Pipeline failed during scheduled run: {e}\n")
        
        print(f"💤 Sleeping for {interval_hours} hours...\n")
        # Sleep in intervals to allow easy KeyboardInterrupt
        for _ in range(interval_hours * 3600):
            await asyncio.sleep(1)

def main():
    """Entry point — run the full OptimaCV pipeline."""
    parser = argparse.ArgumentParser(description="OptimaCV Job Aggregator")
    parser.add_argument("--continuous", action="store_true", help="Run repeatedly every 4 hours")
    parser.add_argument("--interval", type=int, default=4, help="Interval in hours for continuous mode")
    args = parser.parse_args()

    print("\n🏁 OptimaCV Stealth Job Aggregator — Starting...\n")

    try:
        if args.continuous:
            asyncio.run(run_continuously(args.interval))
        else:
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
