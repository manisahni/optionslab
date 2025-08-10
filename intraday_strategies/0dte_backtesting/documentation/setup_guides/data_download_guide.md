# SPY Data Download Guide

## Quick Start

### First Time Download (2 years of data)
```bash
python download_spy_data_incremental.py
```

### Daily/Weekly Updates (only new data)
```bash
python download_spy_data_incremental.py --update
```

## Usage Examples

### 1. Update Mode (Recommended for regular updates)
```bash
# Automatically detects existing SPY.parquet and downloads only new data
python download_spy_data_incremental.py --update
```

### 2. Download Last N Days
```bash
# Download last 30 days of data
python download_spy_data_incremental.py --days 30
```

### 3. Full Download with Custom Years
```bash
# Download 5 years of historical data
python download_spy_data_incremental.py --full --years 5
```

### 4. Dry Run (Preview without downloading)
```bash
# See what would be downloaded without actually downloading
python download_spy_data_incremental.py --update --dry-run
```

### 5. Backup Before Update
```bash
# Create backup of existing file before updating
python download_spy_data_incremental.py --update --backup
```

### 6. Different Symbol
```bash
# Download QQQ data instead of SPY
python download_spy_data_incremental.py --symbol QQQ
```

### 7. Custom IB Gateway Port
```bash
# If using different port than 4002
python download_spy_data_incremental.py --port 7497
```

## Features

- **Incremental Updates**: Only downloads new data, preserving existing data
- **Checkpoint System**: Resume interrupted downloads
- **Memory Efficient**: Saves partial files every 50 days
- **Data Validation**: Checks for gaps in downloaded data
- **Backup Option**: Optionally backup existing data before updates
- **Progress Tracking**: Real-time progress with TQDM

## Monitor Downloads

In a separate terminal, run:
```bash
python monitor_download.py
```

## File Structure

- `SPY.parquet` - Main data file containing all historical data
- `SPY_partial_*.parquet` - Temporary files during download (auto-cleaned)
- `SPY_download_checkpoint.json` - Resume information (auto-cleaned)
- `SPY_backup_*.parquet` - Backup files (if --backup used)

## Typical Workflow

1. **Initial Setup** (one time):
   ```bash
   python download_spy_data_incremental.py --years 2
   ```

2. **Daily Updates** (automated):
   ```bash
   python download_spy_data_incremental.py --update
   ```

3. **Weekly Full Refresh** (optional):
   ```bash
   python download_spy_data_incremental.py --days 10 --backup
   ```

## Notes

- IB Gateway must be running on the specified port (default: 4002)
- Updates are smart - won't re-download existing dates
- All times are in EST (market hours only)
- Data includes 1-minute MIDPOINT bars