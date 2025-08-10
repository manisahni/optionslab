#!/usr/bin/env python3
"""
Zero DTE Database Maintenance System
Tracks database health, performance, and maintenance tasks
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
import pandas as pd
import sqlite3
from typing import Dict, List, Optional
import subprocess
import psutil

# Add the market_data directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from zero_dte_spy_options_database import ZeroDTESPYOptionsDatabase


class ZeroDTEMaintenanceLog:
    """Maintenance logging system for Zero DTE database"""
    
    def __init__(self):
        self.db = ZeroDTESPYOptionsDatabase()
        self.log_dir = os.path.expanduser("~/0dte/maintenance")
        self.db_path = os.path.join(self.log_dir, "maintenance.db")
        
        # Create directories
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Initialize SQLite database for maintenance logs
        self._init_database()
        
        # Configure logging
        log_file = os.path.join(self.log_dir, f"maintenance_{datetime.now().strftime('%Y%m')}.log")
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('Maintenance')
    
    def _init_database(self):
        """Initialize maintenance database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT,
                status TEXT,
                details TEXT,
                metrics TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_metrics (
                date TEXT PRIMARY KEY,
                records_added INTEGER,
                total_records INTEGER,
                total_days INTEGER,
                disk_usage_mb REAL,
                avg_file_size_mb REAL,
                processing_time_sec REAL,
                errors INTEGER,
                warnings INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_quality (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                check_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                date TEXT,
                missing_timestamps INTEGER,
                invalid_prices INTEGER,
                missing_greeks INTEGER,
                spread_anomalies INTEGER,
                quality_score REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_health (
                timestamp DATETIME PRIMARY KEY,
                disk_free_gb REAL,
                memory_usage_pct REAL,
                cpu_usage_pct REAL,
                thetadata_status TEXT,
                api_response_time_ms REAL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def log_event(self, event_type: str, status: str, details: str, metrics: Optional[Dict] = None):
        """Log a maintenance event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO maintenance_log (event_type, status, details, metrics)
            VALUES (?, ?, ?, ?)
        """, (event_type, status, details, json.dumps(metrics) if metrics else None))
        
        conn.commit()
        conn.close()
        
        # Also log to file
        self.logger.info(f"{event_type} - {status}: {details}")
    
    def check_system_health(self):
        """Check and log system health metrics"""
        health = {
            'timestamp': datetime.now().isoformat(),
            'disk_free_gb': psutil.disk_usage('/').free / (1024**3),
            'memory_usage_pct': psutil.virtual_memory().percent,
            'cpu_usage_pct': psutil.cpu_percent(interval=1)
        }
        
        # Check ThetaData status
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            health['thetadata_status'] = 'running' if 'ThetaTerminal' in result.stdout else 'stopped'
        except:
            health['thetadata_status'] = 'unknown'
        
        # Check API response time
        import requests
        import time
        try:
            start = time.time()
            requests.get("http://localhost:25503/v3/", timeout=5)
            health['api_response_time_ms'] = (time.time() - start) * 1000
        except:
            health['api_response_time_ms'] = -1
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO system_health 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(),
            health['disk_free_gb'],
            health['memory_usage_pct'],
            health['cpu_usage_pct'],
            health['thetadata_status'],
            health['api_response_time_ms']
        ))
        
        conn.commit()
        conn.close()
        
        # Log warnings
        if health['disk_free_gb'] < 10:
            self.log_event('SYSTEM_WARNING', 'LOW_DISK', f"Only {health['disk_free_gb']:.1f} GB free")
        
        if health['memory_usage_pct'] > 80:
            self.log_event('SYSTEM_WARNING', 'HIGH_MEMORY', f"Memory usage at {health['memory_usage_pct']:.1f}%")
        
        return health
    
    def check_data_quality(self, date: str):
        """Check data quality for a specific date"""
        df = self.db.load_zero_dte_data(date)
        
        if df.empty:
            return None
        
        quality = {
            'date': date,
            'missing_timestamps': 0,
            'invalid_prices': 0,
            'missing_greeks': 0,
            'spread_anomalies': 0
        }
        
        # Check for missing timestamps (should have 391 per contract)
        expected_timestamps = 391
        for (strike, right), group in df.groupby(['strike', 'right']):
            if len(group) < expected_timestamps:
                quality['missing_timestamps'] += expected_timestamps - len(group)
        
        # Check for invalid prices
        quality['invalid_prices'] = len(df[(df['bid'] < 0) | (df['ask'] < 0) | (df['bid'] > df['ask'])])
        
        # Check for missing Greeks
        quality['missing_greeks'] = len(df[df['delta'].isna() | df['theta'].isna()])
        
        # Check for abnormal spreads (>50% of mid price)
        df['spread_pct'] = (df['ask'] - df['bid']) / df['mid_price']
        quality['spread_anomalies'] = len(df[df['spread_pct'] > 0.5])
        
        # Calculate quality score (0-100)
        # Sum only the numeric values (not the date string)
        total_issues = (quality['missing_timestamps'] + quality['invalid_prices'] + 
                       quality['missing_greeks'] + quality['spread_anomalies'])
        total_possible = len(df)
        quality['quality_score'] = max(0, 100 - (total_issues / total_possible * 100)) if total_possible > 0 else 100
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO data_quality 
            (date, missing_timestamps, invalid_prices, missing_greeks, spread_anomalies, quality_score)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            date,
            quality['missing_timestamps'],
            quality['invalid_prices'],
            quality['missing_greeks'],
            quality['spread_anomalies'],
            quality['quality_score']
        ))
        
        conn.commit()
        conn.close()
        
        return quality
    
    def update_daily_metrics(self, date: str, records_added: int = 0, processing_time: float = 0):
        """Update daily metrics"""
        # Get current database stats
        self.db.metadata = self.db._load_metadata()
        
        # Calculate disk usage
        total_size = 0
        file_count = 0
        for folder in os.listdir(self.db.data_dir):
            if folder.startswith('2025'):
                file_path = os.path.join(self.db.data_dir, folder, f"zero_dte_spy_{folder}.parquet")
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
                    file_count += 1
        
        disk_usage_mb = total_size / (1024**2)
        avg_file_size_mb = disk_usage_mb / file_count if file_count > 0 else 0
        
        # Save metrics
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO daily_metrics 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            date,
            records_added,
            self.db.metadata['total_records'],
            self.db.metadata['total_days'],
            disk_usage_mb,
            avg_file_size_mb,
            processing_time,
            0,  # errors (to be implemented)
            0   # warnings (to be implemented)
        ))
        
        conn.commit()
        conn.close()
    
    def run_maintenance_check(self):
        """Run complete maintenance check"""
        self.logger.info("="*60)
        self.logger.info("RUNNING MAINTENANCE CHECK")
        self.logger.info("="*60)
        
        # 1. System health
        self.logger.info("Checking system health...")
        health = self.check_system_health()
        self.log_event('MAINTENANCE', 'SYSTEM_CHECK', 'System health check completed', health)
        
        # 2. Database integrity
        self.logger.info("Checking database integrity...")
        self.check_database_integrity()
        
        # 3. Data quality for recent days
        self.logger.info("Checking data quality...")
        recent_dates = sorted(self.db.metadata['downloaded_dates'])[-5:]
        for date in recent_dates:
            quality = self.check_data_quality(date)
            if quality and quality['quality_score'] < 95:
                self.log_event('DATA_QUALITY', 'WARNING', 
                             f"Quality score {quality['quality_score']:.1f}% for {date}", quality)
        
        # 4. Cleanup old logs
        self.cleanup_old_logs()
        
        self.logger.info("Maintenance check completed")
        self.log_event('MAINTENANCE', 'COMPLETED', 'Routine maintenance completed successfully')
    
    def check_database_integrity(self):
        """Check database file integrity"""
        issues = []
        
        # Check for missing files
        for date in self.db.metadata['downloaded_dates']:
            file_path = os.path.join(self.db.data_dir, date, f"zero_dte_spy_{date}.parquet")
            if not os.path.exists(file_path):
                issues.append(f"Missing file for {date}")
        
        # Check for corrupted files
        for date in self.db.metadata['downloaded_dates'][-10:]:  # Check last 10 days
            try:
                df = self.db.load_zero_dte_data(date)
                if df.empty:
                    issues.append(f"Empty data for {date}")
            except Exception as e:
                issues.append(f"Corrupted file for {date}: {str(e)}")
        
        if issues:
            self.log_event('INTEGRITY_CHECK', 'ISSUES_FOUND', f"Found {len(issues)} issues", {'issues': issues})
        else:
            self.log_event('INTEGRITY_CHECK', 'PASSED', 'All files verified successfully')
    
    def cleanup_old_logs(self, days_to_keep=30):
        """Clean up old log files"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cleaned = 0
        
        # Clean up log files
        for filename in os.listdir(self.log_dir):
            if filename.endswith('.log'):
                file_path = os.path.join(self.log_dir, filename)
                if datetime.fromtimestamp(os.path.getmtime(file_path)) < cutoff_date:
                    os.remove(file_path)
                    cleaned += 1
        
        if cleaned > 0:
            self.log_event('CLEANUP', 'COMPLETED', f"Removed {cleaned} old log files")
    
    def generate_maintenance_report(self):
        """Generate maintenance report"""
        conn = sqlite3.connect(self.db_path)
        
        # Recent events
        events_df = pd.read_sql_query("""
            SELECT * FROM maintenance_log 
            ORDER BY timestamp DESC 
            LIMIT 20
        """, conn)
        
        # System health trends
        health_df = pd.read_sql_query("""
            SELECT * FROM system_health 
            WHERE timestamp > datetime('now', '-7 days')
            ORDER BY timestamp
        """, conn)
        
        # Data quality summary
        quality_df = pd.read_sql_query("""
            SELECT 
                AVG(quality_score) as avg_quality,
                MIN(quality_score) as min_quality,
                COUNT(*) as checks_performed
            FROM data_quality
            WHERE check_date > datetime('now', '-30 days')
        """, conn)
        
        # Daily metrics
        metrics_df = pd.read_sql_query("""
            SELECT * FROM daily_metrics 
            ORDER BY date DESC 
            LIMIT 30
        """, conn)
        
        conn.close()
        
        # Generate report
        report = {
            'generated_at': datetime.now().isoformat(),
            'recent_events': events_df.to_dict('records'),
            'system_health': {
                'current': health_df.iloc[-1].to_dict() if not health_df.empty else {},
                'avg_disk_free': health_df['disk_free_gb'].mean() if not health_df.empty else 0,
                'avg_memory_usage': health_df['memory_usage_pct'].mean() if not health_df.empty else 0
            },
            'data_quality': quality_df.iloc[0].to_dict() if not quality_df.empty else {},
            'growth_metrics': {
                'total_days': self.db.metadata['total_days'],
                'total_records': self.db.metadata['total_records'],
                'avg_daily_records': metrics_df['records_added'].mean() if not metrics_df.empty else 0
            }
        }
        
        # Save report
        report_path = os.path.join(self.log_dir, f"maintenance_report_{datetime.now().strftime('%Y%m%d')}.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        return report


def view_maintenance_logs():
    """View recent maintenance logs"""
    log = ZeroDTEMaintenanceLog()
    
    conn = sqlite3.connect(log.db_path)
    cursor = conn.cursor()
    
    # Get recent events
    cursor.execute("""
        SELECT timestamp, event_type, status, details 
        FROM maintenance_log 
        ORDER BY timestamp DESC 
        LIMIT 20
    """)
    
    print("="*80)
    print("RECENT MAINTENANCE EVENTS")
    print("="*80)
    print(f"{'Timestamp':<20} {'Event':<20} {'Status':<15} {'Details':<25}")
    print("-"*80)
    
    for row in cursor.fetchall():
        timestamp = datetime.fromisoformat(row[0]).strftime('%Y-%m-%d %H:%M')
        print(f"{timestamp:<20} {row[1]:<20} {row[2]:<15} {row[3][:25]:<25}")
    
    conn.close()


def main():
    """Run maintenance tasks"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Zero DTE Database Maintenance')
    parser.add_argument('--check', action='store_true', help='Run maintenance check')
    parser.add_argument('--report', action='store_true', help='Generate maintenance report')
    parser.add_argument('--view', action='store_true', help='View recent logs')
    parser.add_argument('--quality', help='Check data quality for specific date (YYYYMMDD)')
    
    args = parser.parse_args()
    
    log = ZeroDTEMaintenanceLog()
    
    if args.check:
        log.run_maintenance_check()
    elif args.report:
        report = log.generate_maintenance_report()
        print(f"Report generated: {json.dumps(report, indent=2, default=str)}")
    elif args.view:
        view_maintenance_logs()
    elif args.quality:
        quality = log.check_data_quality(args.quality)
        if quality:
            print(f"Data quality for {args.quality}: {quality['quality_score']:.1f}%")
            print(f"Issues: {json.dumps(quality, indent=2)}")
    else:
        # Default: run maintenance check
        log.run_maintenance_check()


if __name__ == "__main__":
    main()