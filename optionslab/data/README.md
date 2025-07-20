# OptionsLab Data Directory

This directory contains SPY options data files used for backtesting.

## Data Files

- **SPY_OPTIONS_MASTER_20200715_20250711.parquet** - Master file containing 5 years of SPY options data (1.3GB)
- **SPY_OPTIONS_YYYY_COMPLETE.parquet** - Individual yearly files (100-400MB each)

## Data Source

These files were generated using the ThetaData API through the spy_options_downloader utility.
The data includes:
- End-of-day option prices
- Greeks (delta, gamma, theta, vega)
- Implied volatility
- Volume and open interest
- Bid/ask spreads

## Data Coverage

- Start Date: July 15, 2020
- End Date: July 11, 2025
- Underlying: SPY (SPDR S&P 500 ETF)
- Frequency: Daily end-of-day snapshots

## Usage

The OptionsLab app automatically detects and loads these files.
Select your preferred data file when running a backtest:
- Use the master file for multi-year backtests
- Use yearly files for faster loading of specific periods

## Updating Data

To update the data files, use the spy_options_downloader package (separate project).