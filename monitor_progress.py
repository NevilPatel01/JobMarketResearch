#!/usr/bin/env python3
"""
Monitor the progress of the 5000+ job collection.
Run this periodically to check status.
"""

import sys
from pathlib import Path

src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from database.connection import DatabaseConnection
from database.models import JobRaw, JobFeatures, ScraperMetrics
from sqlalchemy import func
import time

def show_progress():
    """Show collection progress."""
    db = DatabaseConnection()
    
    print("\n" + "="*80)
    print("📊 COLLECTION PROGRESS - TARGET: 5,000+ JOBS")
    print("="*80)
    
    with db.get_session() as session:
        # Total counts
        total_jobs = session.query(JobRaw).count()
        total_features = session.query(JobFeatures).count()
        
        # Progress
        target = 5000
        progress_pct = (total_jobs / target) * 100
        
        print(f"\n✅ Total Jobs: {total_jobs:,} / {target:,} ({progress_pct:.1f}%)")
        print(f"✅ Features Extracted: {total_features:,} ({(total_features/total_jobs*100) if total_jobs > 0 else 0:.1f}% coverage)")
        
        # Progress bar
        bar_length = 50
        filled = int(bar_length * total_jobs / target)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"\n[{bar}] {progress_pct:.1f}%")
        
        # Remaining
        remaining = max(0, target - total_jobs)
        print(f"\n🎯 Remaining: {remaining:,} jobs to reach target")
        
        # City breakdown
        print(f"\n📍 TOP 15 CITIES:")
        city_counts = session.query(
            JobRaw.city,
            func.count(JobRaw.job_id).label('count')
        ).group_by(JobRaw.city).order_by(func.count(JobRaw.job_id).desc()).limit(15).all()
        
        for i, (city, count) in enumerate(city_counts, 1):
            print(f"   {i:2d}. {city:20s} {count:4d} jobs")
        
        # Recent jobs
        print(f"\n🆕 RECENT ADDITIONS (last 10):")
        recent = session.query(JobRaw).order_by(JobRaw.created_at.desc()).limit(10).all()
        for job in recent:
            print(f"   • {job.title[:50]:50s} | {job.city}, {job.province}")
        
        # Metrics
        metrics = session.query(ScraperMetrics).order_by(ScraperMetrics.run_date.desc()).limit(5).all()
        if metrics:
            print(f"\n📈 RECENT COLLECTION RUNS:")
            for m in metrics:
                print(f"   • {m.run_date.strftime('%Y-%m-%d %H:%M')}: {m.jobs_collected} collected, {m.jobs_valid} new")
        
        print("\n" + "="*80)
        
        if total_jobs >= target:
            print("🎉 TARGET REACHED! Collection complete!")
        else:
            est_time = remaining * 0.5 / 60  # Rough estimate: 0.5 sec per job
            print(f"⏱️  Estimated time to target: ~{est_time:.0f} minutes")
        
        print("="*80 + "\n")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor job collection progress')
    parser.add_argument('--watch', action='store_true', help='Watch mode - update every 30 seconds')
    parser.add_argument('--interval', type=int, default=30, help='Watch interval in seconds')
    
    args = parser.parse_args()
    
    if args.watch:
        print("📡 WATCH MODE - Press Ctrl+C to stop")
        try:
            while True:
                show_progress()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n\n👋 Monitoring stopped\n")
    else:
        show_progress()
