"""
Utility functions and classes for ThetaData Python client.

This module provides common utilities used throughout the client library,
including retry logic, rate limiting, and helper functions.

---

Common Bulk Endpoints for use with fetch_paginated_csv and fetch_paginated_csv_with_fallback:

- /bulk_hist/option/eod_greeks
    params: root, exp, start_date, end_date
- /bulk_hist/option/quotes
    params: root, exp, start_date, end_date, interval
- /bulk/option/greeks
    params: root, exp
- /bulk/option/quotes
    params: root, exp
- /bulk_hist/option/greeks
    params: root, exp, start_date, end_date

Check the ThetaData API documentation for full details and additional endpoints.

Use fetch_paginated_csv to fetch and paginate CSV data from any endpoint, returning a DataFrame.
Use fetch_paginated_csv_with_fallback to try multiple endpoints in order and return the first successful DataFrame.
"""

import asyncio
import time
from collections import deque
from typing import Dict, Any, TypeVar, Callable, Optional, Union, List, Tuple, cast
from functools import wraps
import logging
from datetime import datetime

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_log,
    after_log,
)
import httpx
import pandas as pd
from io import StringIO


class MinimalThetaDataClient:
    def __init__(self, base_url="http://127.0.0.1:25503/v3"):
        self.base_url = base_url

    async def list_option_expirations(self, symbol):
        url = f"{self.base_url}/list/expirations"
        params = {"root": symbol}
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json().get("data", [])

    async def list_option_strikes(self, symbol, exp):
        url = f"{self.base_url}/list/strikes"
        params = {"root": symbol, "exp": exp}
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json().get("data", [])


def fetch_paginated_csv(
    endpoint: str,
    params: dict,
    base_url: str = "http://127.0.0.1:25510/v2",
    timeout: int = 60,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Generic CSV pagination fetcher for any API endpoint, returning a DataFrame.
        
        Args:
        endpoint: API path after base_url (e.g. '/bulk_hist/option/eod').
        params: Initial query parameters (include 'use_csv': True when needed).
            WARNING: Passing unsupported parameters (e.g. 'fields', 'right') may cause the server to return an error (e.g. 473).
        base_url: Base URL for the API.
        timeout: Request timeout in seconds.
        verbose: If True, print error messages when HTTP errors occur.
        
    Returns:
        A pandas DataFrame concatenating all pages of CSV data, or an empty DataFrame if the request fails.

    Example:
        df = fetch_paginated_csv(
            endpoint='/bulk_hist/option/eod',
            params={
                'root': 'AAPL',
                'exp': '20250117',
                'start_date': '20241107',
                'end_date': '20241107',
                'use_csv': True
            }
        )
        print(df.head())
    """
    url = f"{base_url}{endpoint}"
    frames = []
    first = True
    try:
        while url:
            req_params = params if first else {}
            resp = httpx.get(url, params=req_params, timeout=timeout)
            resp.raise_for_status()
            df_page = pd.read_csv(StringIO(resp.text))
            if not df_page.empty:
                frames.append(df_page)
            next_page = resp.headers.get("Next-Page")
            if not next_page or next_page == "null":
                break
            url = next_page
            first = False
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    except httpx.HTTPStatusError as e:
        if verbose:
            print(f"Request failed: {e.response.status_code} - {e.response.text}")
            print("Returning empty DataFrame. This may mean the endpoint is not enabled, the data is not available, or your parameters are not supported.")
        return pd.DataFrame()


def fetch_option_chain_at_time(
    root: str,
    exp: str,
    date: str,
    ivl: int,
    base_url: str = "http://127.0.0.1:25510/v2",
    timeout: int = 60,
    verbose: bool = True,
    **kwargs
) -> pd.DataFrame:
    """
    Fetch the option chain snapshot at a specific time of day for a given symbol and expiration.
    Uses the /bulk_at_time/option/quote endpoint and fetch_paginated_csv.
    
    Args:
        root: Underlying symbol (e.g., 'AAPL')
        exp: Expiration date (YYYYMMDD as string)
        date: Date for the snapshot (YYYYMMDD as string)
        ivl: Milliseconds since midnight ET (e.g., 37800000 for 10:30am)
        base_url: Base URL for the API.
        timeout: Request timeout in seconds.
        verbose: If True, print error messages when HTTP errors occur.
        **kwargs: Additional parameters to pass to the endpoint (e.g., right, strike, use_csv, etc.)
        
    Returns:
        DataFrame of the option chain snapshot at the specified time.

    Example:
        df = fetch_option_chain_at_time(
            root='AAPL',
            exp='20250117',
            date='20241107',
            ivl=37800000,  # 10:30am ET
            use_csv=True
        )
        print(df.head())
    """
    params = {
        'root': root,
        'exp': exp,
        'start_date': date,
        'end_date': date,
        'ivl': ivl,
        'use_csv': True
    }
    params.update(kwargs)
    return fetch_paginated_csv(
        endpoint='/bulk_at_time/option/quote',
        params=params,
        base_url=base_url,
        timeout=timeout,
        verbose=verbose
    )


def discover_and_download_eod_chain(
    symbol,
    date,
    target_dte=None,
    reference_date=None,
    base_url="http://127.0.0.1:25510/v2",
    verbose=True
):
    """
    Discover available option expirations for a symbol and download the EOD option chain
    for the expiration whose DTE (from reference_date) is closest to target_dte.
    If target_dte is None, uses the first expiration.
    Prints detailed debugging output if verbose is True.
    """
    from .utils import fetch_paginated_csv
    from datetime import datetime

    # Step 1: Discover expirations
    exp_df = fetch_paginated_csv(
        endpoint='/list/expirations',
        params={'root': symbol, 'use_csv': True},
        base_url=base_url
    )
    expirations = exp_df['date'].tolist() if 'date' in exp_df.columns else []
    if verbose:
        print(f"Expirations for {symbol}: {expirations}")
    if not expirations:
        print(f"No expirations found for {symbol}.")
        return None

    # Step 2: Find expiration with DTE closest to target_dte
    if target_dte is not None:
        if reference_date is None:
            reference_date = date
        if isinstance(reference_date, str):
            ref_dt = datetime.strptime(reference_date, "%Y%m%d")
        else:
            ref_dt = reference_date
        if verbose:
            print(f"Reference date: {ref_dt.strftime('%Y-%m-%d')}")
            print("All expirations and DTEs:")
            for exp in expirations:
                dte = (datetime.strptime(str(exp), "%Y%m%d") - ref_dt).days
                print(f"  Exp: {exp}  DTE: {dte}")
        # Find expiration with DTE closest to target_dte
        best_exp = min(
            expirations,
            key=lambda exp: abs((datetime.strptime(str(exp), "%Y%m%d") - ref_dt).days - target_dte)
        )
        exp = best_exp
        dte = (datetime.strptime(str(exp), "%Y%m%d") - ref_dt).days
        if verbose:
            print(f"Selected expiration: {exp} (DTE: {dte} from {reference_date})")
    else:
        exp = expirations[0]
        if verbose:
            print(f"Using expiration: {exp}")

    # Step 3: Download EOD option chain
    df = fetch_paginated_csv(
        endpoint='/bulk_hist/option/eod',
        params={
            'root': symbol,
            'exp': exp,
            'start_date': date,
            'end_date': date,
            'use_csv': True
        },
        base_url=base_url
    )
    if verbose:
        print(f"Downloaded DataFrame shape: {df.shape}")
        print(df.head())
    return df


def discover_and_download_contract_history(
    symbol: str,
    reference_date: str,
    target_dte: Optional[int] = None,
    strike_filter: Optional[Tuple[int, int]] = None,  # (min_strike, max_strike) in 1/1000th dollars
    right: str = 'C',
    data_type: str = 'eod',  # 'eod' or 'ohlc'
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    ivl: Optional[int] = None,  # Only for OHLC, in ms
    strike_selection: str = 'ATM',  # 'ATM', 'OTM', 'ITM', or 'MID'
    base_url: str = "http://127.0.0.1:25510/v2",
    verbose: bool = True
) -> tuple:
    """
    Discover and download option contract history for a symbol, with DTE and strike filtering.

    This function:
      1. Discovers all available expirations for the symbol.
      2. Selects the expiration whose DTE (from reference_date) is closest to target_dte.
      3. Discovers all strikes for the selected expiration.
      4. Filters strikes by a given range (if provided).
      5. Selects a strike by moneyness: ATM (middle), OTM (highest), ITM (lowest), or MID (middle).
      6. Downloads EOD or OHLC data for the selected contract and date range.
    
    Args:
        symbol: Underlying symbol (e.g., 'AAPL').
        reference_date: Date (YYYYMMDD) to calculate DTE from.
        target_dte: Desired days to expiration (int). If None, uses the first expiration.
        strike_filter: Tuple (min_strike, max_strike) in 1/1000th dollars, or None for all.
        right: 'C' for call, 'P' for put.
        data_type: 'eod' for end-of-day, 'ohlc' for intraday bars.
        start_date: Start date (YYYYMMDD) for data. Defaults to reference_date.
        end_date: End date (YYYYMMDD) for data. Defaults to reference_date.
        ivl: Interval in ms for OHLC data (e.g., 60000 for 1 min bars).
        strike_selection: 'ATM' (middle), 'OTM' (highest), 'ITM' (lowest), or 'MID' (middle).
        base_url: Base URL for the ThetaData API.
        verbose: If True, print detailed logs.
        
    Returns:
        df: pandas DataFrame with the contract history.
        best_exp: Selected expiration (YYYYMMDD as int).
        chosen_strike: Selected strike (int, 1/1000th dollars).
        exp_dte: Days to expiration from reference_date (int).

    Example:
        df, exp, strike, dte = discover_and_download_contract_history(
            symbol='AAPL',
            reference_date='20200601',
            target_dte=30,
            strike_filter=(200000, 250000),
            right='C',
            data_type='eod',
            start_date='20200601',
            end_date='20200630',
            strike_selection='ATM',
            verbose=True
        )
    """
    from thetadata import fetch_paginated_csv
    from datetime import datetime

    # Step 1: Discover expirations
    exp_df = fetch_paginated_csv(
        endpoint='/list/expirations',
        params={'root': symbol, 'use_csv': True},
        base_url=base_url
    )
    expirations = exp_df['date'].tolist() if 'date' in exp_df.columns else []
    if not expirations:
        print(f"No expirations found for {symbol}.")
        return None, None, None, None

    # Step 2: Filter by DTE
    if isinstance(reference_date, str):
        ref_dt = datetime.strptime(reference_date, "%Y%m%d")
    else:
        ref_dt = reference_date
    if target_dte is not None:
        best_exp = min(
            expirations,
            key=lambda exp: abs((datetime.strptime(str(exp), "%Y%m%d") - ref_dt).days - target_dte)
        )
    else:
        best_exp = expirations[0]
    exp_dte = (datetime.strptime(str(best_exp), "%Y%m%d") - ref_dt).days
    if verbose:
        print(f"Selected expiration: {best_exp} (DTE: {exp_dte} from {reference_date})")

    # Step 3: Discover strikes
    strikes_df = fetch_paginated_csv(
        endpoint='/list/strikes',
        params={'root': symbol, 'exp': best_exp, 'use_csv': True},
        base_url=base_url
    )
    strikes = strikes_df['strike'].tolist() if 'strike' in strikes_df.columns else []
    if verbose:
        print(f"All strikes for {symbol} {best_exp}: {strikes}")
        print(f"Number of strikes before filtering: {len(strikes)}")
    if not strikes:
        print(f"No strikes found for {symbol} {best_exp}.")
        return None, best_exp, None, exp_dte

    # Step 4: Filter strikes
    if strike_filter:
        min_strike, max_strike = strike_filter
        if verbose:
            print(f"Applying strike filter: {strike_filter}")
        filtered_strikes = [s for s in strikes if min_strike <= s <= max_strike]
    else:
        filtered_strikes = strikes
    if verbose:
        print(f"Number of strikes after filtering: {len(filtered_strikes)}")
        print(f"Filtered strikes: {filtered_strikes}")
    if not filtered_strikes:
        print(f"No strikes match filter {strike_filter}.")
        return None, best_exp, None, exp_dte

    # Step 5: Select strike
    if strike_selection == 'ATM' or strike_selection == 'MID':
        idx = len(filtered_strikes) // 2
    elif strike_selection == 'OTM':
        idx = -1
    elif strike_selection == 'ITM':
        idx = 0
    else:
        idx = len(filtered_strikes) // 2
    chosen_strike = filtered_strikes[idx]
    if verbose:
        print(f"Selected strike: {chosen_strike} ({strike_selection}, index {idx})")

    # Step 6: Download data
    params = {
        'root': symbol,
        'exp': best_exp,
        'strike': chosen_strike,
        'right': right,
        'start_date': start_date or reference_date,
        'end_date': end_date or reference_date,
        'use_csv': True
    }
    endpoint = '/hist/option/eod' if data_type == 'eod' else '/hist/option/ohlc'
    if data_type == 'ohlc' and ivl is not None:
        params['ivl'] = ivl

    df = fetch_paginated_csv(
        endpoint=endpoint,
        params=params,
        base_url=base_url
    )
    if verbose:
        print(df.head())
    return df, best_exp, chosen_strike, exp_dte

from typing import Optional, Tuple, List, Union
from datetime import datetime

def get_expirations(symbol: str, base_url: str = "http://127.0.0.1:25510/v2") -> List[int]:
    """
    Fetch all available option expirations for a symbol.
    Returns a list of expiration dates (YYYYMMDD as integers).
    """
    from thetadata import fetch_paginated_csv
    df = fetch_paginated_csv(
        endpoint='/list/expirations',
        params={'root': symbol, 'use_csv': True},
        base_url=base_url
    )
    return df['date'].tolist() if 'date' in df.columns else []

def filter_expirations_by_dte(expirations: List[int], reference_date: Union[str, datetime], target_dte: int) -> int:
    """
    Select the expiration whose DTE from reference_date is closest to target_dte.
    Returns the expiration as an integer (YYYYMMDD).
    """
    if isinstance(reference_date, str):
        ref_dt = datetime.strptime(reference_date, "%Y%m%d")
    else:
        ref_dt = reference_date
    return min(
        expirations,
        key=lambda exp: abs((datetime.strptime(str(exp), "%Y%m%d") - ref_dt).days - target_dte)
    )

def get_strikes(symbol: str, exp: int, base_url: str = "http://127.0.0.1:25510/v2") -> List[int]:
    """
    Fetch all available strikes for a symbol and expiration.
    Returns a list of strikes (integers, 1/1000th dollars).
    """
    from thetadata import fetch_paginated_csv
    df = fetch_paginated_csv(
        endpoint='/list/strikes',
        params={'root': symbol, 'exp': exp, 'use_csv': True},
        base_url=base_url
    )
    return df['strike'].tolist() if 'strike' in df.columns else []

def filter_strikes(strikes: List[int], strike_filter: Optional[Tuple[int, int]] = None) -> List[int]:
    """
    Filter strikes by a (min_strike, max_strike) tuple. If None, returns all strikes.
    """
    if strike_filter:
        min_strike, max_strike = strike_filter
        return [s for s in strikes if min_strike <= s <= max_strike]
    return strikes

def select_strike(filtered_strikes: List[int], selection: str = 'ATM') -> Optional[int]:
    """
    Select a strike from the filtered list by moneyness:
    'ATM' or 'MID' = middle, 'OTM' = highest, 'ITM' = lowest.
    Returns the selected strike or None if the list is empty.
    """
    if not filtered_strikes:
        return None
    if selection == 'ATM' or selection == 'MID':
        idx = len(filtered_strikes) // 2
    elif selection == 'OTM':
        idx = -1
    elif selection == 'ITM':
        idx = 0
            else:
        idx = len(filtered_strikes) // 2
    return filtered_strikes[idx]

def download_contract_history(
    symbol: str,
    exp: int,
    strike: int,
    right: str,
    data_type: str,
    start_date: str,
    end_date: str,
    ivl: Optional[int] = None,
    base_url: str = "http://127.0.0.1:25510/v2"
):
    """
    Download EOD or OHLC data for a specific contract.
    Returns a pandas DataFrame, deduplicated by date (keeps last ms_of_day per date).
    """
    from thetadata import fetch_paginated_csv
    import pandas as pd
    params = {
        'root': symbol,
        'exp': int(exp),
        'strike': int(strike),
        'right': right,
        'start_date': int(start_date),
        'end_date': int(end_date),
        'use_csv': True
    }
    endpoint = '/hist/option/eod' if data_type == 'eod' else '/hist/option/ohlc'
    if data_type == 'ohlc' and ivl is not None:
        params['ivl'] = ivl
    df = fetch_paginated_csv(endpoint=endpoint, params=params, base_url=base_url)
    if not df.empty and 'date' in df.columns and 'ms_of_day' in df.columns:
        df = df.sort_values('ms_of_day').drop_duplicates(subset=['date'], keep='last')
    return df

from typing import Optional

def get_greeks_for_chain(
    symbol: str,
    exp: int,
    date: str,
    right: Optional[str] = None,
    base_url: str = "http://127.0.0.1:25510/v2"
) -> pd.DataFrame:
    """
    Fetch EOD Greeks for all contracts in a chain for a given expiration and date.
    Optionally filter by right ('C' or 'P').
    Returns a DataFrame with columns including 'strike', 'right', 'delta', 'iv', etc.
    """
    from thetadata import fetch_paginated_csv
    params = {
        'root': symbol,
        'exp': int(exp),
        'start_date': int(date),
        'end_date': int(date),
        'use_csv': True
    }
    endpoint = '/bulk_hist/option/eod_greeks'
    df = fetch_paginated_csv(endpoint=endpoint, params=params, base_url=base_url)
    if right is not None and 'right' in df.columns:
        df = df[df['right'] == right]
    return df

def list_greek_columns(df: pd.DataFrame) -> list:
    """
    Return a list of columns in the DataFrame that are likely Greeks or implied volatility.
    This is useful for quickly seeing which Greeks are available for filtering or analysis.
    Example:
        >>> list_greek_columns(df)
        ['delta', 'gamma', 'vega', 'implied_vol', ...]
    """
    greek_keywords = [
        'delta', 'gamma', 'vega', 'theta', 'rho', 'vanna', 'charm', 'vomma', 'veta', 'vera',
        'speed', 'zomma', 'color', 'ultima', 'd1', 'd2', 'implied_vol', 'implied_volatility', 'iv'
    ]
    return [col for col in df.columns if any(key in col.lower() for key in greek_keywords)]

def filter_by_greek(
    df: pd.DataFrame,
    greek: str,
    target_value: Optional[float] = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    method: str = 'closest'
) -> pd.DataFrame:
    """
    Filter a DataFrame of option contracts by a Greek (e.g., delta, iv, vega, etc.).

    Features:
    - Accepts common aliases (e.g., 'iv', 'implied_volatility', 'vol') for implied volatility.
    - Case-insensitive matching for Greek names.
    - If the requested Greek is not found, raises a helpful error listing available Greek columns.
    - If target_value is set and method='closest', returns the row(s) with Greek closest to target_value.
    - If min_value/max_value are set, returns rows within that range.
    - Always returns a DataFrame (even if empty).

    Example:
        >>> df_iv = filter_by_greek(df, 'iv', min_value=0.2, max_value=0.4)
        >>> df_delta = filter_by_greek(df, 'delta', target_value=0.5)
        >>> df_vega = filter_by_greek(df, 'vega', min_value=0.1)
    
    Args:
        df: DataFrame of contracts (must include Greek columns).
        greek: Name or alias of the Greek to filter by (e.g., 'delta', 'iv', 'implied_vol').
        target_value: If set, finds the contract(s) with Greek closest to this value.
        min_value: If set, filters for contracts with Greek >= min_value.
        max_value: If set, filters for contracts with Greek <= max_value.
        method: 'closest' (default) for closest-to-target filtering.
        
    Returns:
        Filtered DataFrame of contracts.
        
    Raises:
        ValueError: If the requested Greek is not found in the DataFrame columns.
    """
    # Alias mapping for common Greek/IV names
    greek_aliases = {
        'iv': 'implied_vol',
        'implied_volatility': 'implied_vol',
        'impliedvol': 'implied_vol',
        'vol': 'implied_vol',
        'vega': 'vega',
        'delta': 'delta',
        'gamma': 'gamma',
        'theta': 'theta',
        'rho': 'rho',
        # Add more as needed
    }
    # Case-insensitive matching
    greek_lower = greek.lower()
    columns_lower = {col.lower(): col for col in df.columns}
    # Direct match
    if greek_lower in columns_lower:
        greek_col = columns_lower[greek_lower]
    # Alias match
    elif greek_lower in greek_aliases and greek_aliases[greek_lower] in columns_lower:
        greek_col = columns_lower[greek_aliases[greek_lower]]
    else:
        # Try partial match (e.g., 'vol' in 'implied_vol')
        for alias in [greek_lower] + list(greek_aliases.values()):
            for col in df.columns:
                if alias in col.lower():
                    greek_col = col
                    break
            else:
                continue
            break
        else:
            available = list_greek_columns(df)
            raise ValueError(f"Greek '{greek}' not found in DataFrame columns. Available Greek columns: {available}")
    # Now use greek_col for filtering
    if target_value is not None and method == 'closest':
        df = df.copy()
        df['greek_diff'] = (df[greek_col] - target_value).abs()
        min_diff = df['greek_diff'].min()
        idx = df.index[df['greek_diff'] == min_diff].tolist()
        if len(idx) == 0:
            return df.drop(columns=['greek_diff']).iloc[[]]
        result = df.loc[[i for i in idx]].drop(columns=['greek_diff'])  # type: ignore
        return result
    if min_value is not None or max_value is not None:
        mask = (pd.Series([True] * len(df), index=df.index)).astype(bool)
        if min_value is not None:
            mask &= df[greek_col] >= min_value
        if max_value is not None:
            mask &= df[greek_col] <= max_value
        filtered_idx = df.index[mask].tolist()
        if len(filtered_idx) == 0:
            return df.iloc[[]]
        filtered = df.loc[[i for i in filtered_idx]]  # type: ignore
        return filtered
    return df

from typing import Optional, Callable

def track_option_over_time(
    symbol: str,
    start_date: str,
    end_date: str,
    right: str = "C",
    dte: int = 30,
    selection_rule: str = "greek",  # 'greek', 'moneyness', 'fixed_strike', 'custom'
    greek: str = "delta",
    greek_target: float = 0.5,
    moneyness_type: str = "ATM",  # ATM, OTM, ITM, etc.
    strike_offset: int = 0,  # Not used in select_strike, kept for future extension
    fixed_strike: Optional[int] = None,
    min_volume: int = 1,
    custom_selector: Optional[Callable[[pd.DataFrame], pd.DataFrame]] = None
) -> pd.DataFrame:  # type: ignore
    """
    Generalized function to track an option contract over time according to a selection rule.
    For each business day in [start_date, end_date], selects a contract based on the rule and returns a DataFrame with contract metadata and Greeks.
    
    Args:
        symbol: Underlying symbol (e.g., 'AAPL').
        start_date: Start date (YYYYMMDD).
        end_date: End date (YYYYMMDD).
        right: 'C' for call, 'P' for put.
        dte: Days to expiration for rolling window.
        selection_rule: How to select the contract each day ('greek', 'moneyness', 'fixed_strike', 'custom').
        greek: Greek to target (if selection_rule='greek').
        greek_target: Value of the Greek to target (if selection_rule='greek').
        moneyness_type: Moneyness type to select (if selection_rule='moneyness').
        strike_offset: Offset from ATM (not currently used).
        fixed_strike: Use this strike for all dates (if selection_rule='fixed_strike').
        min_volume: Minimum volume for contract selection.
        custom_selector: Callable for custom selection logic (if selection_rule='custom').
        
    Returns:
        DataFrame with columns: date, exp, strike, close, volume, implied_vol, and all available Greeks for each selected contract.
    """
    import pandas as pd
    from thetadata import (
        get_expirations, filter_expirations_by_dte, get_greeks_for_chain, filter_by_greek, download_contract_history,
        filter_strikes, select_strike, get_strikes
    )
    window = pd.date_range(start_date, end_date, freq="B").strftime("%Y%m%d")
    results = []
    for ref_date in window:
        expirations = get_expirations(symbol)
        if not expirations:
            continue
        exp = filter_expirations_by_dte(expirations, ref_date, dte)
        df_greeks = get_greeks_for_chain(symbol, exp, ref_date, right=right)
        if not isinstance(df_greeks, pd.DataFrame) or df_greeks.empty:
            continue
        df_greeks = df_greeks[df_greeks['volume'] >= min_volume]
        if df_greeks.empty:
            continue
        # Selection logic
        if selection_rule == "greek":
            if not isinstance(df_greeks, pd.DataFrame):
                continue
            df_target = filter_by_greek(df_greeks, greek, target_value=greek_target)
            if isinstance(df_target, pd.Series):
                df_target = df_target.to_frame().T
        elif selection_rule == "moneyness":
            strikes = get_strikes(symbol, exp)
            filtered_strikes = filter_strikes(strikes)
            strike = select_strike(filtered_strikes, selection=moneyness_type)
            if strike is None:
                continue
            df_target = df_greeks[df_greeks['strike'] == strike]
            if isinstance(df_target, pd.Series):
                df_target = df_target.to_frame().T
        elif selection_rule == "fixed_strike":
            if fixed_strike is None:
                continue
            df_target = df_greeks[df_greeks['strike'] == fixed_strike]
            if isinstance(df_target, pd.Series):
                df_target = df_target.to_frame().T
        elif selection_rule == "custom" and custom_selector is not None:
            df_target = custom_selector(df_greeks)
            if isinstance(df_target, pd.Series):
                df_target = df_target.to_frame().T
        else:
            raise ValueError(f"Unknown selection_rule: {selection_rule}")
        # Robust type check and conversion for df_target
        if isinstance(df_target, pd.Series):
            df_target = df_target.to_frame().T
        if not isinstance(df_target, pd.DataFrame) or df_target.empty:
            continue
        df_target = cast(pd.DataFrame, df_target)
        strike = df_target['strike'].iloc[0]  # type: ignore
        df_eod = download_contract_history(
            symbol=symbol, exp=exp, strike=strike, right=right,
            data_type='eod', start_date=ref_date, end_date=ref_date
        )
        if not isinstance(df_eod, pd.DataFrame) or df_eod.empty:
            continue
        row = {
            'date': ref_date,
            'exp': exp,
            'strike': strike,
            'close': df_eod['close'].iloc[0],
            'volume': df_target['volume'].iloc[0],
        }
        for col in df_target.columns:
            if col not in row and col not in ['date', 'exp', 'strike', 'close', 'volume']:
                row[col] = df_target[col].iloc[0]
        results.append(row)
    return pd.DataFrame(results)

# Deprecated/legacy wrappers for backward compatibility
track_rolling_atm_option_and_greeks = track_option_over_time  # For ATM, use selection_rule='greek', greek='delta', greek_target=0.5
track_rolling_option_by_target_delta = track_option_over_time  # For delta, use selection_rule='greek', greek='delta', greek_target=your_value

from typing import Optional

def get_spot_price(client, symbol: str, date: str) -> Optional[float]:
    """
    Fetches the EOD close price for a stock on a given date using the ThetaData client.
    Args:
        client: An instance of ThetaDataTerminalClient.
        symbol: Stock symbol (e.g., 'AAPL').
        date: Date in 'YYYYMMDD' format.
    Returns:
        EOD close price as float, or None if not available.
    """
    ohlc = client.get_stock_ohlc_history_sync(symbol, date, date, interval_size=86400000)
    if ohlc and 'close' in ohlc[0]:
        return ohlc[0]['close']
    return None

def get_current_spot_price(client, symbol: str) -> Optional[float]:
    """
    Fetches the current/last spot price for a stock using the ThetaData client.
    Args:
        client: An instance of ThetaDataTerminalClient.
        symbol: Stock symbol (e.g., 'AAPL').
    Returns:
        Last or close price as float, or None if not available.
    """
    quote = client.get_stock_quote_snapshot_sync(symbol)
    return quote.get('last') or quote.get('close')

def get_stock_ohlc_history(
    symbol: str,
    start_date: str,
    end_date: str,
    interval_size: int = 86400000,  # 1 day
    base_url: str = "http://127.0.0.1:25510/v2"
) -> list:
    """
    Fetches historical OHLC data for a stock over a date range.
    Returns: List of dicts with 'date', 'open', 'high', 'low', 'close', etc.
    """
    import httpx
    endpoint = "/hist/stock/ohlc"
    url = f"{base_url}{endpoint}"
    params = {
        "root": symbol,
        "start_date": int(start_date),
        "end_date": int(end_date),
        "ivl": int(interval_size),
        "use_csv": False
    }
    resp = httpx.get(url, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    # Expecting data to be a dict with a 'data' key containing a list of dicts
    return data.get("data", [])
def get_option_trades(
    symbol: str,
    exp: int,
    strike: int,
    right: str,
    start_date: str,
    end_date: str,
    use_csv: bool = True,
    base_url: str = "http://127.0.0.1:25510/v2"
) -> list:
    """
    Fetch all trades for a specific option contract (tick data) from /hist/option/trade.
    Returns a list of dicts (if use_csv=False) or a DataFrame (if use_csv=True).
    """
    import httpx
    import csv
    import pandas as pd
    params = {
        "root": symbol,
        "exp": exp,
        "strike": strike,
        "right": right,
        "start_date": start_date,
        "end_date": end_date,
        "use_csv": use_csv
    }
    url = f"{base_url}/hist/option/trade"
    results = []
    while url is not None:
        resp = httpx.get(url, params=params, timeout=60)
        resp.raise_for_status()
        if use_csv:
            lines = resp.text.splitlines()
            if not lines or len(lines) < 2:
                break
            header = lines[0].split(",")
            for row in lines[1:]:
                if not row.strip():
                    continue
                fields = row.split(",")
                row_dict = dict(zip(header, fields))
                results.append(row_dict)
        else:
            data = resp.json()
            results.extend(data.get("response", []))
        if 'Next-Page' in resp.headers and resp.headers['Next-Page'] != "null":
            url = resp.headers['Next-Page']
            params = None
        else:
            url = None
    if use_csv:
        return pd.DataFrame(results) if results else pd.DataFrame()
    return results

def get_bulk_option_trades(
    symbol: str,
    exp: int,
    start_date: str,
    end_date: str,
    use_csv: bool = False,
    base_url: str = "http://127.0.0.1:25510/v2"
) -> list:
    """
    Fetch all trades for all contracts for a symbol/expiration from /bulk_hist/option/trade.
    Returns a list of dicts (parsed from JSON) or a DataFrame if use_csv=True.
    """
    import httpx
    import csv
    import pandas as pd
    params = {
        "root": symbol,
        "exp": exp,
        "start_date": start_date,
        "end_date": end_date,
        "use_csv": use_csv
    }
    url = f"{base_url}/bulk_hist/option/trade"
    results = []
    while url is not None:
        resp = httpx.get(url, params=params, timeout=60)
        resp.raise_for_status()
        if use_csv:
            lines = resp.text.splitlines()
            if not lines or len(lines) < 2:
                break
            header = lines[0].split(",")
            for row in lines[1:]:
                if not row.strip():
                    continue
                fields = row.split(",")
                row_dict = dict(zip(header, fields))
                results.append(row_dict)
        else:
            data = resp.json()
            results.extend(data.get("response", []))
        if 'Next-Page' in resp.headers and resp.headers['Next-Page'] != "null":
            url = resp.headers['Next-Page']
            params = None
        else:
            url = None
    if use_csv:
        return pd.DataFrame(results) if results else pd.DataFrame()
    return results
