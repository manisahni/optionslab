#!/usr/bin/env python3
"""
Unified 0DTE Database Monitor
Consolidates all monitoring functionality
"""

import os
import sys
import argparse
import time
from datetime import datetime
import pandas as pd

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.zero_dte_spy_options_database import ZeroDTESPYOptionsDatabase


class UnifiedMonitor:
    """Single tool for all monitoring needs"""
    
    def __init__(self):
        self.db = ZeroDTESPYOptionsDatabase()
    
    def show_summary(self, detailed: bool = False):
        """Show database summary"""
        print("="*80)
        print("0DTE SPY OPTIONS DATABASE SUMMARY")
        print("="*80)
        
        metadata = self.db.metadata
        
        # Basic stats
        print(f"\nDatabase Location: {self.db.data_dir}")
        print(f"Total Days: {metadata.get('total_days', 0)}")
        print(f"Date Range: {metadata.get('date_range', {}).get('start', 'N/A')} to {metadata.get('date_range', {}).get('end', 'N/A')}")
        print(f"Total Records: {metadata.get('total_records', 0):,}")
        
        # Storage stats
        total_size = sum(
            os.path.getsize(os.path.join(self.db.data_dir, d, f))
            for d in os.listdir(self.db.data_dir)
            if os.path.isdir(os.path.join(self.db.data_dir, d))
            for f in os.listdir(os.path.join(self.db.data_dir, d))
            if f.endswith('.parquet')
        ) / (1024 * 1024)  # MB
        
        print(f"Database Size: {total_size:.1f} MB")
        
        if metadata.get('total_days', 0) > 0:
            print(f"Average MB/Day: {total_size / metadata['total_days']:.2f}")
            print(f"Average Records/Day: {metadata.get('total_records', 0) // metadata['total_days']:,}")
        
        # Completion status
        if metadata.get('date_range'):
            start_dt = pd.to_datetime(metadata['date_range']['start'])
            end_dt = pd.to_datetime(metadata['date_range']['end'])
            expected_days = len(pd.bdate_range(start_dt, end_dt))
            completion_pct = (metadata.get('total_days', 0) / expected_days * 100) if expected_days > 0 else 0
            
            print(f"\nCompletion: {completion_pct:.1f}% ({metadata.get('total_days', 0)}/{expected_days} trading days)")
        
        # Recent activity
        if metadata.get('last_updated'):
            print(f"\nLast Updated: {metadata['last_updated']}")
        
        if detailed and metadata.get('downloaded_dates'):
            dates = sorted(metadata['downloaded_dates'])
            print(f"\nFirst 5 dates: {', '.join(dates[:5])}")
            print(f"Last 5 dates: {', '.join(dates[-5:])}")
            
            # Check for gaps
            all_dates = set(dates)
            expected_dates = set(
                d.strftime('%Y%m%d') 
                for d in pd.bdate_range(dates[0], dates[-1])
            )
            missing = expected_dates - all_dates
            
            if missing:
                print(f"\nMissing dates: {len(missing)}")
                print(f"Examples: {', '.join(sorted(missing)[:5])}")
        
        print("="*80)
    
    def watch_downloads(self, interval: int = 5):
        """Live monitoring of download progress"""
        print("Monitoring download progress... (Press Ctrl+C to stop)")
        print("="*80)
        
        last_count = self.db.metadata.get('total_days', 0)
        last_records = self.db.metadata.get('total_records', 0)
        
        while True:
            try:
                # Reload metadata
                self.db.metadata = self.db._load_metadata()
                current_count = self.db.metadata.get('total_days', 0)
                current_records = self.db.metadata.get('total_records', 0)
                
                # Clear screen
                os.system('clear' if os.name == 'posix' else 'cls')
                
                # Show current status
                print(f"Download Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("="*80)
                print(f"Total Days: {current_count}")
                print(f"Total Records: {current_records:,}")
                
                # Show progress
                if current_count > last_count:
                    new_days = current_count - last_count
                    new_records = current_records - last_records
                    print(f"\n✓ New data: {new_days} days, {new_records:,} records")
                    
                    # Show recent downloads
                    recent = sorted(self.db.metadata.get('downloaded_dates', []))[-5:]
                    print(f"Recent: {', '.join(recent)}")
                    
                    last_count = current_count
                    last_records = current_records
                else:
                    print("\nWaiting for new downloads...")
                
                # Show download rate
                if hasattr(self, 'start_time'):
                    elapsed = (datetime.now() - self.start_time).total_seconds() / 60
                    if elapsed > 0:
                        rate = (current_count - self.initial_count) / elapsed
                        print(f"\nDownload rate: {rate:.1f} days/minute")
                else:
                    self.start_time = datetime.now()
                    self.initial_count = current_count
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n\nMonitoring stopped.")
                break
            except Exception as e:
                print(f"\nError: {e}")
                time.sleep(interval)
    
    def check_data_quality(self, sample_dates: int = 5):
        """Quick data quality check"""
        print("Running data quality check...")
        print("="*80)
        
        # Get sample of dates
        all_dates = sorted(self.db.metadata.get('downloaded_dates', []))
        if not all_dates:
            print("No data to check!")
            return
        
        # Sample evenly across range
        if len(all_dates) <= sample_dates:
            check_dates = all_dates
        else:
            indices = [int(i * len(all_dates) / sample_dates) for i in range(sample_dates)]
            check_dates = [all_dates[i] for i in indices]
        
        print(f"Checking {len(check_dates)} sample dates...\n")
        
        issues = []
        
        for date in check_dates:
            print(f"Checking {date}...")
            try:
                df = self.db.load_zero_dte_data(date)
                
                # Check for data issues
                zero_bids = len(df[df['bid'] == 0])
                zero_asks = len(df[df['ask'] == 0])
                bad_spreads = len(df[df['ask'] < df['bid']])
                
                # Check delta distribution
                calls = df[df['right'] == 'CALL']
                delta_1 = len(calls[calls['delta'] == 1.0])
                
                if zero_bids > 10 or zero_asks > 10:
                    issues.append(f"{date}: Many zero prices (bid: {zero_bids}, ask: {zero_asks})")
                
                if bad_spreads > 0:
                    issues.append(f"{date}: {bad_spreads} options with ask < bid")
                
                if delta_1 > len(calls) * 0.5:
                    issues.append(f"{date}: {delta_1}/{len(calls)} calls have delta=1.0")
                    
            except Exception as e:
                issues.append(f"{date}: Error loading - {e}")
        
        # Summary
        print(f"\n{'='*80}")
        if issues:
            print(f"Found {len(issues)} potential issues:")
            for issue in issues[:10]:  # Show first 10
                print(f"  - {issue}")
            if len(issues) > 10:
                print(f"  ... and {len(issues) - 10} more")
        else:
            print("✓ No major issues found!")
        
        print("="*80)


def main():
    parser = argparse.ArgumentParser(
        description='Unified 0DTE Database Monitor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show summary
  %(prog)s --summary
  
  # Show detailed summary  
  %(prog)s --summary --detailed
  
  # Watch downloads live
  %(prog)s --watch
  
  # Check data quality
  %(prog)s --quality
        """
    )
    
    parser.add_argument('--summary', '-s', action='store_true',
                      help='Show database summary')
    parser.add_argument('--watch', '-w', action='store_true',
                      help='Watch downloads in real-time')
    parser.add_argument('--quality', '-q', action='store_true',
                      help='Check data quality')
    parser.add_argument('--detailed', '-d', action='store_true',
                      help='Show detailed information')
    parser.add_argument('--interval', '-i', type=int, default=5,
                      help='Update interval for watch mode (seconds)')
    
    args = parser.parse_args()
    
    if not any([args.summary, args.watch, args.quality]):
        parser.error('Must specify an action: --summary, --watch, or --quality')
    
    monitor = UnifiedMonitor()
    
    if args.summary:
        monitor.show_summary(detailed=args.detailed)
    elif args.watch:
        monitor.watch_downloads(interval=args.interval)
    elif args.quality:
        monitor.check_data_quality()


if __name__ == '__main__':
    main()