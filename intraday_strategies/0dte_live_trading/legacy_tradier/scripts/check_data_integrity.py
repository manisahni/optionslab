#!/usr/bin/env python3
"""
Check data integrity and identify issues with backfill
"""

import sqlite3
from datetime import datetime

conn = sqlite3.connect('database/market_data.db')
cur = conn.cursor()

print('=' * 70)
print('DATA INTEGRITY CHECK')
print('=' * 70)

# Check SPY data continuity
cur.execute('''
    SELECT 
        date(timestamp) as date,
        COUNT(*) as records,
        MIN(time(timestamp)) as first_time,
        MAX(time(timestamp)) as last_time,
        COUNT(DISTINCT time(timestamp)) as unique_times
    FROM spy_prices
    WHERE date(timestamp) >= '2025-08-06'
    GROUP BY date(timestamp)
    ORDER BY date
''')

print('\nSPY Data Summary:')
print('-' * 50)
for row in cur.fetchall():
    expected = 391 if row[0] < '2025-08-08' else 641  # More records on Aug 8
    status = '✅' if row[1] >= expected - 10 else '⚠️'
    print(f'{status} {row[0]}: {row[1]} records, {row[2]} to {row[3]}')
    
# Check for gaps in Aug 8
print('\nAug 8 Key Timestamps:')
print('-' * 50)
cur.execute('''
    SELECT timestamp, close
    FROM spy_prices  
    WHERE date(timestamp) = '2025-08-08'
    AND time(timestamp) IN ('14:29:00', '14:30:00', '14:31:00', '15:00:00', '15:30:00', '16:00:00')
    ORDER BY timestamp
''')

for row in cur.fetchall():
    time_label = ''
    if '14:29' in row[0]: time_label = ' (Last original data)'
    if '14:30' in row[0]: time_label = ' (First bridge data)'
    if '15:00' in row[0]: time_label = ' (VegaAware entry)'
    if '15:30' in row[0]: time_label = ' (VegaAware exit)'
    if '16:00' in row[0]: time_label = ' (Market close)'
    print(f'  {row[0]}: ${row[1]:.2f}{time_label}')

# Check the transition area closely
print('\nData Transition Analysis (2:28-2:35 PM):')
print('-' * 50)
cur.execute('''
    SELECT 
        timestamp, 
        close,
        close - LAG(close) OVER (ORDER BY timestamp) as change,
        volume
    FROM spy_prices
    WHERE timestamp BETWEEN '2025-08-08 14:28:00' AND '2025-08-08 14:35:00'
    ORDER BY timestamp
''')

rows = cur.fetchall()
for i, row in enumerate(rows):
    if row[2] is not None:
        change_str = f'  Change: ${row[2]:+.2f}'
        if abs(row[2]) > 1.0:
            change_str += ' ⚠️ LARGE JUMP'
    else:
        change_str = ''
    
    source = 'Original' if '14:29' in row[0] or '14:28' in row[0] else 'Backfilled'
    print(f'  {row[0]}: ${row[1]:.2f} (Vol: {row[3]:,}) [{source}]{change_str}')

# Check if there are duplicate timestamps
print('\nDuplicate Check:')
print('-' * 50)
cur.execute('''
    SELECT timestamp, COUNT(*) as count
    FROM spy_prices
    WHERE date(timestamp) = '2025-08-08'
    GROUP BY timestamp
    HAVING COUNT(*) > 1
''')
dups = cur.fetchall()
if dups:
    print(f'  ⚠️ Found {len(dups)} duplicate timestamps!')
    for dup in dups[:5]:
        print(f'    {dup[0]}: {dup[1]} records')
else:
    print('  ✅ No duplicate timestamps found')

# Check price continuity
print('\nPrice Continuity Check:')
print('-' * 50)
cur.execute('''
    SELECT 
        MAX(close - LAG(close) OVER (ORDER BY timestamp)) as max_jump,
        MIN(close - LAG(close) OVER (ORDER BY timestamp)) as max_drop,
        AVG(ABS(close - LAG(close) OVER (ORDER BY timestamp))) as avg_change
    FROM spy_prices
    WHERE date(timestamp) = '2025-08-08'
''')
stats = cur.fetchone()
print(f'  Max price jump: ${stats[0]:.2f}')
print(f'  Max price drop: ${stats[1]:.2f}')
print(f'  Avg price change: ${stats[2]:.2f}')

if abs(stats[0]) > 2.0 or abs(stats[1]) > 2.0:
    print('  ⚠️ WARNING: Large price discontinuities detected!')

# Check options data alignment
print('\nOptions Data Check:')
print('-' * 50)
cur.execute('''
    SELECT 
        option_type,
        strike,
        COUNT(*) as records,
        MIN(timestamp) as first,
        MAX(timestamp) as last
    FROM options_data
    WHERE date(timestamp) = '2025-08-08'
    GROUP BY option_type, strike
''')
for row in cur.fetchall():
    print(f'  {row[0].upper()} ${row[1]:.0f}: {row[2]} records, {row[3]} to {row[4]}')

print('\n' + '=' * 70)
print('ISSUES FOUND:')
print('=' * 70)

issues = []

# Check for issues
if abs(stats[0]) > 2.0 or abs(stats[1]) > 2.0:
    issues.append('Large price jumps in SPY data (possible bad interpolation)')

if dups:
    issues.append(f'{len(dups)} duplicate timestamps found')

# Check if options align with SPY
cur.execute('''
    SELECT COUNT(*)
    FROM options_data o
    WHERE date(o.timestamp) = '2025-08-08'
    AND NOT EXISTS (
        SELECT 1 FROM spy_prices s 
        WHERE s.timestamp = o.timestamp
    )
''')
orphan_options = cur.fetchone()[0]
if orphan_options > 0:
    issues.append(f'{orphan_options} options records without matching SPY data')

if issues:
    for issue in issues:
        print(f'⚠️ {issue}')
else:
    print('✅ No major issues found')

print('\nRECOMMENDATION:')
if issues:
    print('Consider cleaning and re-importing the data to fix discontinuities')
else:
    print('Data appears to be properly integrated')

conn.close()