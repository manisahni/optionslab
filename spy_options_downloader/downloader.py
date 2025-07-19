import os
import glob
import time
from datetime import date, timedelta
from thetadata_client.utils import fetch_paginated_csv
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed


def download_and_store_spy_options(
    symbol='SPY',
    base_url="http://127.0.0.1:25510/v2",
    parquet_dir="spy_options_parquet",
    error_log="spy_options_download_errors.log",
    max_retries=3,
    retry_delay=5,
    max_workers=6,
    lookback_years=2
):
    os.makedirs(parquet_dir, exist_ok=True)
    today = date.today()
    start_date = today - timedelta(days=lookback_years*365)
    def generate_trading_dates(start, end):
        d = start
        dates = []
        while d <= end:
            if d.weekday() < 5:
                dates.append(int(d.strftime('%Y%m%d')))
            d += timedelta(days=1)
        return dates
    date_list = generate_trading_dates(start_date, today)
    existing_files = glob.glob(os.path.join(parquet_dir, f'{symbol.lower()}_options_eod_*.parquet'))
    existing_dates = set(int(f.split('_')[-1].split('.')[0]) for f in existing_files)
    missing_dates = [dt for dt in date_list if dt not in existing_dates]
    print(f"Total trading days: {len(date_list)}")
    print(f"Already downloaded: {len(existing_dates)}")
    print(f"Missing: {len(missing_dates)}")

    def download_and_save(dt):
        for attempt in range(1, max_retries + 1):
            try:
                params_eod = {
                    'root': symbol,
                    'exp': 0,
                    'start_date': dt,
                    'end_date': dt,
                    'use_csv': True,
                    'pretty_time': True
                }
                df_eod = fetch_paginated_csv(
                    endpoint='/bulk_hist/option/eod',
                    params=params_eod,
                    base_url=base_url
                )
                params_greeks = {
                    'root': symbol,
                    'exp': 0,
                    'start_date': dt,
                    'end_date': dt,
                    'use_csv': True,
                    'pretty_time': True
                }
                df_greeks = fetch_paginated_csv(
                    endpoint='/bulk_hist/option/eod_greeks',
                    params=params_greeks,
                    base_url=base_url
                )
                merge_cols = ['expiration', 'strike', 'right', 'date']
                if not df_eod.empty and not df_greeks.empty:
                    df_merged = df_eod.merge(df_greeks, on=merge_cols, how='left', suffixes=('', '_greeks'))
                    parquet_path = os.path.join(parquet_dir, f'{symbol.lower()}_options_eod_{dt}.parquet')
                    df_merged.to_parquet(parquet_path)
                    return (dt, None)
                else:
                    msg = f"Skipping {dt}: No data."
                    return (dt, msg)
            except Exception as e:
                if attempt < max_retries:
                    time.sleep(retry_delay)
                else:
                    msg = f"Error on {dt} after {max_retries} attempts: {e}"
                    return (dt, msg)

    with open(error_log, "a") as elog, ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_and_save, dt): dt for dt in missing_dates}
        for future in tqdm(as_completed(futures), total=len(futures), desc=f"Downloading {symbol} options"):
            dt, err = future.result()
            if err:
                print(err)
                elog.write(err + "\n")
    print("Download complete!")


if __name__ == "__main__":
    # Modified to download 5 years total (existing 2 + additional 3)
    download_and_store_spy_options(lookback_years=5) 