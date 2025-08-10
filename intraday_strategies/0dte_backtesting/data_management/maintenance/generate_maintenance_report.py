#!/usr/bin/env python3
"""
Generate and display maintenance report
"""

import json
from datetime import datetime
from zero_dte_maintenance import ZeroDTEMaintenanceLog

def main():
    print("GENERATING MAINTENANCE REPORT")
    print("="*60)
    
    # Initialize maintenance log
    log = ZeroDTEMaintenanceLog()
    
    # Generate report
    report = log.generate_maintenance_report()
    
    # Display summary
    print(f"\nReport Generated: {report['generated_at']}")
    print("\nSYSTEM HEALTH:")
    if report['system_health']['current']:
        current = report['system_health']['current']
        print(f"  Disk Free: {current.get('disk_free_gb', 0):.1f} GB")
        print(f"  Memory Usage: {current.get('memory_usage_pct', 0):.1f}%")
        print(f"  CPU Usage: {current.get('cpu_usage_pct', 0):.1f}%")
        print(f"  ThetaData: {current.get('thetadata_status', 'unknown')}")
    
    print("\nDATA QUALITY:")
    quality = report['data_quality']
    if quality:
        print(f"  Average Score: {quality.get('avg_quality', 0):.1f}%")
        print(f"  Minimum Score: {quality.get('min_quality', 0):.1f}%")
        print(f"  Checks Performed: {quality.get('checks_performed', 0)}")
    
    print("\nGROWTH METRICS:")
    growth = report['growth_metrics']
    print(f"  Total Days: {growth['total_days']}")
    print(f"  Total Records: {growth['total_records']:,}")
    print(f"  Avg Daily Records: {growth['avg_daily_records']:,.0f}")
    
    print("\nRECENT EVENTS:")
    for event in report['recent_events'][:5]:
        timestamp = datetime.fromisoformat(event['timestamp']).strftime('%Y-%m-%d %H:%M')
        print(f"  [{timestamp}] {event['event_type']}: {event['status']}")
    
    # Save location
    report_file = f"/Users/nish_macbook/0dte/maintenance/maintenance_report_{datetime.now().strftime('%Y%m%d')}.json"
    print(f"\nFull report saved to: {report_file}")
    
if __name__ == "__main__":
    main()