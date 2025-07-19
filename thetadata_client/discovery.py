from typing import List, Optional, Tuple, Union
from datetime import datetime

async def discover_option_contracts(
    client,
    symbol: str,
    target_dte: Optional[int] = None,
    strike_range: Optional[Tuple[float, float]] = None,
    right: str = "C",
    dte_window: int = 3,
    for_date: Optional[Union[str, datetime]] = None,
    verbose: bool = True
) -> List[dict]:
    """
    Discover option contracts for a symbol, with optional DTE and strike filtering.

    Args:
        client: An instance of your ThetaData client (must have list_option_expirations and list_option_strikes).
        symbol: Underlying symbol (e.g., 'AAPL').
        target_dte: Target days to expiration (int), or None for all.
        strike_range: Tuple (min_strike, max_strike), or None for all.
        right: 'C' for calls, 'P' for puts.
        dte_window: Acceptable window around target_dte (e.g., ±3 days).
        for_date: Date to calculate DTE from (YYYYMMDD str or datetime), or None for today.
        verbose: If True, print progress.

    Returns:
        List of contract dicts: {'root', 'exp', 'strike', 'right'}

    Example:
        contracts = await discover_option_contracts(
            client,
            symbol='AAPL',
            target_dte=7,
            dte_window=2,
            strike_range=(5000, 6000),
            right='C',
            for_date='20120601'
        )
        print(f"Discovered {len(contracts)} contracts.")
        print(contracts[:5])
    """
    if for_date is not None:
        if isinstance(for_date, str):
            today = datetime.strptime(for_date, "%Y%m%d")
        elif isinstance(for_date, datetime):
            today = for_date
        else:
            raise ValueError("for_date must be None, a 'YYYYMMDD' string, or a datetime object")
    else:
        today = datetime.today()

    contracts = []
    expirations = await client.list_option_expirations(symbol)
    for exp in expirations:
        exp_date = datetime.strptime(str(exp), "%Y%m%d")
        dte = (exp_date - today).days
        if target_dte is not None and abs(dte - target_dte) > dte_window:
            continue
        strikes = await client.list_option_strikes(symbol, exp)
        strikes = [s / 1000.0 if s > 1000 else s for s in strikes]
        if verbose:
            print(f"Expiration: {exp} (DTE: {dte}) -> First 10 Strikes: {strikes[:10]} ... total: {len(strikes)}")
        for strike in strikes:
            if strike_range and not (strike_range[0] <= strike <= strike_range[1]):
                continue
            contracts.append({"root": symbol, "exp": exp, "strike": strike, "right": right})
    if verbose:
        print(f"Discovered {len(contracts)} contracts matching criteria.")
    return contracts 