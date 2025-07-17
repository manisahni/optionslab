# SPY Options Downloader

This folder contains scripts for downloading and analyzing SPY options data from ThetaData API.

## Structure

```
spy_options_downloader/
├── downloader.py              # Main script to download SPY options data
├── check_coverage.py          # Analyze date and delta coverage
├── check_duplicates.py        # Check for duplicate dates/records
├── check_structure.py         # Display parquet file structure
├── coverage_summary.py        # Generate coverage summary report
├── spy_options_parquet/       # Downloaded data files (499 files, ~600MB)
└── spy_options_download_errors.log  # Error log
```

## Usage

### Download Data
```bash
cd spy_options_downloader
python downloader.py
```

The downloader will:
- Download 2 years of SPY options end-of-day data
- Combine pricing data with Greeks calculations
- Save as parquet files (one per trading day)
- Skip already downloaded dates (duplicate prevention)

### Analyze Data

Check coverage and data quality:
```bash
python check_coverage.py      # Detailed coverage analysis
python coverage_summary.py    # Summary report
python check_structure.py     # View file structure
python check_duplicates.py    # Verify no duplicates
```

## Data Format

Each parquet file contains:
- **8,000-10,000 option contracts** per day
- **59 columns** including:
  - Option identifiers (root, expiration, strike, right)
  - Market data (open, high, low, close, volume)
  - Bid/Ask spreads
  - Complete Greeks (delta, gamma, theta, vega, rho, etc.)
  - Implied volatility
  - Underlying price

## Requirements

```bash
pip install pandas pyarrow tqdm
```

## Configuration

In `downloader.py`, you can modify:
- `lookback_years`: Number of years to download (default: 2)
- `max_workers`: Parallel download threads (default: 6)
- `base_url`: ThetaData API endpoint (default: localhost:25510)