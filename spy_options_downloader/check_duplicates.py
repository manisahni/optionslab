import pandas as pd
import glob
import os
from collections import Counter

# Get all parquet files
parquet_files = sorted(glob.glob('spy_options_parquet/*.parquet'))

print("=== CHECKING FOR DUPLICATE DATES ===\n")

# Extract dates from filenames
dates_from_filenames = []
for file in parquet_files:
    date_str = os.path.basename(file).split('_')[-1].split('.')[0]
    dates_from_filenames.append(date_str)

# Count occurrences of each date
date_counts = Counter(dates_from_filenames)

# Find duplicates
duplicates = {date: count for date, count in date_counts.items() if count > 1}

if duplicates:
    print(f"⚠️  DUPLICATE DATES FOUND: {len(duplicates)}")
    for date, count in sorted(duplicates.items()):
        print(f"   - {date}: {count} files")
else:
    print("✅ No duplicate dates in filenames")

print(f"\nTotal files: {len(parquet_files)}")
print(f"Unique dates: {len(date_counts)}")

# Check within files for duplicate records
print("\n=== CHECKING FOR DUPLICATE RECORDS WITHIN FILES ===")

# Sample check on a few files
sample_files = [parquet_files[0], parquet_files[len(parquet_files)//2], parquet_files[-1]]

for file in sample_files:
    date_str = os.path.basename(file).split('_')[-1].split('.')[0]
    df = pd.read_parquet(file)
    
    # Define what makes a record unique (option contract)
    unique_cols = ['expiration', 'strike', 'right']
    
    # Check for duplicates
    duplicated = df.duplicated(subset=unique_cols, keep=False)
    num_duplicates = duplicated.sum()
    
    print(f"\nFile: {date_str}")
    print(f"Total records: {len(df):,}")
    print(f"Duplicate records: {num_duplicates:,}")
    
    if num_duplicates > 0:
        # Show some examples
        dup_df = df[duplicated].sort_values(unique_cols)
        print("Examples of duplicates:")
        print(dup_df[unique_cols + ['bid', 'ask', 'volume']].head(10))

# Check if the downloader script has duplicate prevention
print("\n=== CHECKING DOWNLOADER SCRIPT FOR DUPLICATE PREVENTION ===")

with open('downloader.py', 'r') as f:
    downloader_content = f.read()

# Look for duplicate prevention mechanisms
checks = [
    ('existing_files check', 'existing_files' in downloader_content),
    ('existing_dates tracking', 'existing_dates' in downloader_content),
    ('missing_dates calculation', 'missing_dates' in downloader_content),
    ('File overwrite protection', 'exist_ok=True' in downloader_content or 'os.path.exists' in downloader_content)
]

for check_name, found in checks:
    status = "✅" if found else "❌"
    print(f"{status} {check_name}")

# Show the actual duplicate prevention code
print("\n📝 Duplicate prevention code in downloader.py:")
print("-" * 50)

# Extract relevant lines
lines = downloader_content.split('\n')
for i, line in enumerate(lines):
    if 'existing_files' in line or 'existing_dates' in line or 'missing_dates' in line:
        # Show context (3 lines before and after)
        start = max(0, i-2)
        end = min(len(lines), i+3)
        for j in range(start, end):
            print(f"{j+1:4d}: {lines[j]}")
        print()

# Additional check: see if files would be overwritten
print("\n=== FILE OVERWRITE BEHAVIOR ===")
print("Checking if downloader would overwrite existing files...")

# Look for to_parquet usage
for i, line in enumerate(lines):
    if 'to_parquet' in line:
        print(f"\nLine {i+1}: {line.strip()}")
        # Check if there's any existence check before this
        start = max(0, i-5)
        for j in range(start, i):
            if 'exists' in lines[j] or 'isfile' in lines[j]:
                print(f"  Protection found at line {j+1}: {lines[j].strip()}")