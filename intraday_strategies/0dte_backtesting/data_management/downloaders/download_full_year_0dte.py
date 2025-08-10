#!/usr/bin/env python3
"""
Download Full Year of 0DTE SPY Options Data
Handles large-scale historical data download with progress tracking
"""

import os
import sys
import time
import json
import requests
from datetime import datetime, timedelta
import pandas as pd

# Add the market_data directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from zero_dte_spy_options_database import ZeroDTESPYOptionsDatabase


class YearlyDownloader:
    """Download a full year of 0DTE options data"""
    
    def __init__(self):
        self.db = ZeroDTESPYOptionsDatabase()
        self.progress_file = os.path.expanduser("~/0dte/download_progress.json")
        self.failed_dates = []
        self.session = requests.Session()
        
    def get_trading_days(self, start_date, end_date):
        """Generate list of trading days between dates"""
        
        # US market holidays for 2024-2025
        holidays = {
            # 2024 holidays
            "20240101", "20240115", "20240219", "20240329",
            "20240527", "20240619", "20240704", "20240902",
            "20241128", "20241225",
            # 2025 holidays
            "20250101", "20250120", "20250217", "20250418",
            "20250526", "20250619", "20250704", "20250901",
            "20251127", "20251225"
        }
        
        trading_days = []
        current = datetime.strptime(start_date, "%Y%m%d")
        end = datetime.strptime(end_date, "%Y%m%d")
        
        while current <= end:
            # Skip weekends
            if current.weekday() < 5:
                date_str = current.strftime("%Y%m%d")
                # Skip holidays
                if date_str not in holidays:
                    trading_days.append(date_str)
            current += timedelta(days=1)
        
        return trading_days
    
    def load_progress(self):
        """Load download progress"""
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {
            "downloaded_dates": [],
            "failed_dates": [],
            "last_update": None
        }
    
    def save_progress(self, progress):
        """Save download progress"""
        progress["last_update"] = datetime.now().isoformat()
        os.makedirs(os.path.dirname(self.progress_file), exist_ok=True)
        with open(self.progress_file, 'w') as f:
            json.dump(progress, f, indent=2)
    
    def download_year(self, start_date=None, end_date=None):
        """Download full year of data"""
        
        # Default to one year from today
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
        
        print(f"\n{'='*80}")
        print(f"DOWNLOADING 0DTE SPY OPTIONS DATA")
        print(f"Date Range: {start_date} to {end_date}")
        print(f"{'='*80}\n")
        
        # Get all trading days
        all_trading_days = self.get_trading_days(start_date, end_date)
        print(f"Total trading days: {len(all_trading_days)}")
        
        # Load progress
        progress = self.load_progress()
        existing_dates = set(self.db.metadata.get('downloaded_dates', []))
        already_downloaded = set(progress.get('downloaded_dates', [])) | existing_dates
        
        # Filter out already downloaded dates
        dates_to_download = [d for d in all_trading_days if d not in already_downloaded]
        
        print(f"Already downloaded: {len(already_downloaded)} days")
        print(f"Remaining to download: {len(dates_to_download)} days")
        
        if not dates_to_download:
            print("\nAll dates already downloaded!")
            return
        
        # Estimate time and size
        avg_time_per_day = 15  # seconds
        avg_size_per_day = 0.5  # MB
        total_time_est = len(dates_to_download) * avg_time_per_day
        total_size_est = len(dates_to_download) * avg_size_per_day
        
        print(f"\nEstimated download time: {total_time_est/60:.1f} minutes")
        print(f"Estimated data size: {total_size_est:.1f} MB")
        
        # Confirm download
        response = input("\nProceed with download? (y/n): ")
        if response.lower() != 'y':
            print("Download cancelled.")
            return
        
        # Download in monthly batches
        print(f"\n{'='*80}")
        print("STARTING DOWNLOAD")
        print(f"{'='*80}\n")
        
        start_time = time.time()
        total_downloaded = 0
        total_records = 0
        failed_dates = []
        
        for i, date in enumerate(dates_to_download):
            # Progress indicator
            pct_complete = (i / len(dates_to_download)) * 100
            elapsed = time.time() - start_time
            if i > 0:
                eta = (elapsed / i) * (len(dates_to_download) - i)
                eta_str = f"{eta/60:.1f} min"
            else:
                eta_str = "calculating..."
            
            print(f"\r[{pct_complete:5.1f}%] Downloading {date} ({i+1}/{len(dates_to_download)}) - ETA: {eta_str}", 
                  end="", flush=True)
            
            try:
                # Download the date
                records = self.db.download_zero_dte_options_for_date(date, force=True)
                
                if records > 0:
                    total_downloaded += 1
                    total_records += records
                    progress['downloaded_dates'].append(date)
                else:
                    failed_dates.append(date)
                    progress['failed_dates'].append(date)
                
                # Save progress every 10 dates
                if (i + 1) % 10 == 0:
                    self.save_progress(progress)
                
                # Rate limiting - avoid overwhelming the API
                time.sleep(0.5)
                
            except KeyboardInterrupt:
                print("\n\nDownload interrupted by user.")
                self.save_progress(progress)
                break
                
            except Exception as e:
                print(f"\nError downloading {date}: {e}")
                failed_dates.append(date)
                progress['failed_dates'].append(date)
                # Continue with next date
                time.sleep(1)
        
        # Final progress save
        self.save_progress(progress)
        
        # Summary
        elapsed_total = time.time() - start_time
        print(f"\n\n{'='*80}")
        print("DOWNLOAD SUMMARY")
        print(f"{'='*80}")
        print(f"Total time: {elapsed_total/60:.1f} minutes")
        print(f"Successfully downloaded: {total_downloaded} days")
        print(f"Failed: {len(failed_dates)} days")
        print(f"Total records: {total_records:,}")
        print(f"Average records per day: {total_records/total_downloaded:,.0f}" if total_downloaded > 0 else "N/A")
        
        if failed_dates:
            print(f"\nFailed dates: {', '.join(failed_dates[:10])}")
            if len(failed_dates) > 10:
                print(f"... and {len(failed_dates) - 10} more")
            print("\nRun the script again to retry failed dates.")
        
        # Update database metadata
        print("\nUpdating database metadata...")
        self.db._update_metadata()
        
        print(f"\n✅ Download complete!")
        print(f"Database now contains {self.db.metadata['total_days']} days of data")
        print(f"Date range: {self.db.metadata['date_range']['start']} to {self.db.metadata['date_range']['end']}")
        print(f"Total size: {self.get_database_size()}")
    
    def get_database_size(self):
        """Get total database size"""
        total_size = 0
        for root, dirs, files in os.walk(self.db.data_dir):
            for file in files:
                if file.endswith('.parquet'):
                    total_size += os.path.getsize(os.path.join(root, file))
        return f"{total_size / (1024**2):.1f} MB"
    
    def retry_failed_dates(self):
        """Retry downloading failed dates"""
        progress = self.load_progress()
        failed = progress.get('failed_dates', [])
        
        if not failed:
            print("No failed dates to retry!")
            return
        
        print(f"\nRetrying {len(failed)} failed dates...")
        
        # Clear failed dates and try again
        progress['failed_dates'] = []
        self.save_progress(progress)
        
        # Create a temporary list of dates to download
        self.download_year(min(failed), max(failed))


def main():
    """Main download function"""
    downloader = YearlyDownloader()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--retry':
            downloader.retry_failed_dates()
        elif sys.argv[1] == '--status':
            progress = downloader.load_progress()
            print(f"Downloaded: {len(progress.get('downloaded_dates', []))} days")
            print(f"Failed: {len(progress.get('failed_dates', []))} days")
            print(f"Last update: {progress.get('last_update', 'Never')}")
        else:
            print("Usage: python download_full_year_0dte.py [--retry|--status]")
    else:
        # Download full year
        downloader.download_year()


if __name__ == "__main__":
    main()