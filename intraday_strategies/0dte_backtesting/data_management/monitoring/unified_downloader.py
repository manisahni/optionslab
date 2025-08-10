#!/usr/bin/env python3
"""
Unified 0DTE Options Data Downloader
Consolidates all download functionality into one configurable tool
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
import pandas as pd

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.zero_dte_spy_options_database import ZeroDTESPYOptionsDatabase


class UnifiedDownloader:
    """Single tool for all 0DTE download needs"""
    
    def __init__(self):
        self.db = ZeroDTESPYOptionsDatabase()
        
    def download_date_range(self, start_date: str, end_date: str, 
                          skip_existing: bool = True, 
                          verbose: bool = False):
        """
        Download data for a date range
        
        Args:
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)
            skip_existing: Skip dates that already have data
            verbose: Print detailed progress
        """
        print(f"Downloading 0DTE data from {start_date} to {end_date}")
        
        # Get trading days in range
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        # Generate business days
        business_days = pd.bdate_range(start, end)
        dates_to_download = [d.strftime('%Y%m%d') for d in business_days]
        
        # Check existing if skip_existing
        if skip_existing:
            existing = set(self.db.metadata.get('downloaded_dates', []))
            dates_to_download = [d for d in dates_to_download if d not in existing]
            if verbose:
                print(f"Skipping {len(existing)} already downloaded dates")
        
        print(f"Downloading {len(dates_to_download)} days...")
        
        success_count = 0
        failed_dates = []
        
        for i, date in enumerate(dates_to_download, 1):
            if verbose:
                print(f"\n[{i}/{len(dates_to_download)}] Downloading {date}...")
            
            try:
                records = self.db.download_zero_dte_options_for_date(date)
                if records > 0:
                    success_count += 1
                    if verbose:
                        print(f"  ✓ Downloaded {records} records")
                else:
                    failed_dates.append(date)
                    if verbose:
                        print(f"  ✗ No data available")
            except Exception as e:
                failed_dates.append(date)
                if verbose:
                    print(f"  ✗ Error: {e}")
        
        # Summary
        print(f"\nDownload complete!")
        print(f"  Success: {success_count} days")
        print(f"  Failed: {len(failed_dates)} days")
        if failed_dates and verbose:
            print(f"  Failed dates: {', '.join(failed_dates[:10])}")
            if len(failed_dates) > 10:
                print(f"  ... and {len(failed_dates) - 10} more")
                
        return success_count, failed_dates
    
    def download_recent_days(self, days: int = 5, verbose: bool = False):
        """Download most recent N trading days"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days * 2)  # Account for weekends
        
        return self.download_date_range(
            start_date.strftime('%Y%m%d'),
            end_date.strftime('%Y%m%d'),
            skip_existing=True,
            verbose=verbose
        )
    
    def download_missing(self, verbose: bool = False):
        """Download any missing dates in the database range"""
        metadata = self.db.metadata
        if not metadata.get('date_range'):
            print("No existing data range found")
            return 0, []
            
        start = metadata['date_range']['start']
        end = metadata['date_range']['end']
        
        print(f"Checking for missing dates between {start} and {end}")
        
        # Get all business days in range
        start_dt = pd.to_datetime(start)
        end_dt = pd.to_datetime(end)
        all_days = pd.bdate_range(start_dt, end_dt)
        all_days_str = set(d.strftime('%Y%m%d') for d in all_days)
        
        # Find missing
        existing = set(metadata.get('downloaded_dates', []))
        missing = all_days_str - existing
        
        if not missing:
            print("No missing dates found!")
            return 0, []
        
        print(f"Found {len(missing)} missing dates")
        
        # Download missing
        success_count = 0
        failed_dates = []
        
        for date in sorted(missing):
            if verbose:
                print(f"Downloading {date}...")
            try:
                records = self.db.download_zero_dte_options_for_date(date)
                if records > 0:
                    success_count += 1
                else:
                    failed_dates.append(date)
            except Exception as e:
                failed_dates.append(date)
                if verbose:
                    print(f"  Error: {e}")
        
        return success_count, failed_dates
    
    def show_status(self):
        """Show current database status"""
        summary = self.db.database_summary()
        print(summary)


def main():
    parser = argparse.ArgumentParser(
        description='Unified 0DTE Options Data Downloader',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download last 5 days
  %(prog)s --recent 5
  
  # Download specific date range
  %(prog)s --start 20250701 --end 20250731
  
  # Download missing dates
  %(prog)s --missing
  
  # Show database status
  %(prog)s --status
        """
    )
    
    # Action arguments
    parser.add_argument('--recent', type=int, metavar='DAYS',
                      help='Download most recent N days')
    parser.add_argument('--start', type=str, metavar='YYYYMMDD',
                      help='Start date for range download')
    parser.add_argument('--end', type=str, metavar='YYYYMMDD',
                      help='End date for range download')
    parser.add_argument('--missing', action='store_true',
                      help='Download missing dates in existing range')
    parser.add_argument('--status', action='store_true',
                      help='Show database status')
    
    # Options
    parser.add_argument('--force', action='store_true',
                      help='Re-download existing dates')
    parser.add_argument('-v', '--verbose', action='store_true',
                      help='Verbose output')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not any([args.recent, args.start, args.missing, args.status]):
        parser.error('Must specify an action: --recent, --start/--end, --missing, or --status')
    
    if args.start and not args.end:
        parser.error('--start requires --end')
    
    # Execute
    downloader = UnifiedDownloader()
    
    if args.status:
        downloader.show_status()
    elif args.recent:
        downloader.download_recent_days(args.recent, args.verbose)
    elif args.start and args.end:
        downloader.download_date_range(
            args.start, args.end, 
            skip_existing=not args.force,
            verbose=args.verbose
        )
    elif args.missing:
        downloader.download_missing(args.verbose)


if __name__ == '__main__':
    main()