-- Tradier Market Data Cache Schema
-- SQLite database for storing historical and real-time market data

-- SPY price data (1-minute bars)
CREATE TABLE IF NOT EXISTS spy_prices (
    timestamp DATETIME PRIMARY KEY,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume INTEGER,
    vwap REAL,
    session_type TEXT DEFAULT 'regular',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create index for fast date range queries
CREATE INDEX IF NOT EXISTS idx_spy_prices_date ON spy_prices(date(timestamp));

-- Options data with Greeks
CREATE TABLE IF NOT EXISTS options_data (
    timestamp DATETIME NOT NULL,
    symbol TEXT NOT NULL,
    underlying TEXT NOT NULL,
    strike REAL NOT NULL,
    option_type TEXT NOT NULL CHECK(option_type IN ('call', 'put')),
    expiry DATE NOT NULL,
    bid REAL,
    ask REAL,
    last REAL,
    mid REAL GENERATED ALWAYS AS ((bid + ask) / 2.0) STORED,
    volume INTEGER DEFAULT 0,
    open_interest INTEGER DEFAULT 0,
    iv REAL,
    delta REAL,
    gamma REAL,
    theta REAL,
    vega REAL,
    rho REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (timestamp, symbol)
);

-- Indexes for options queries
CREATE INDEX IF NOT EXISTS idx_options_strike ON options_data(strike);
CREATE INDEX IF NOT EXISTS idx_options_expiry ON options_data(expiry);
CREATE INDEX IF NOT EXISTS idx_options_timestamp ON options_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_options_underlying ON options_data(underlying, timestamp);

-- Metadata tracking for data completeness
CREATE TABLE IF NOT EXISTS data_status (
    date DATE PRIMARY KEY,
    spy_loaded BOOLEAN DEFAULT 0,
    spy_records INTEGER DEFAULT 0,
    options_loaded BOOLEAN DEFAULT 0,
    options_records INTEGER DEFAULT 0,
    last_update DATETIME,
    update_count INTEGER DEFAULT 0,
    notes TEXT
);

-- Real-time update log
CREATE TABLE IF NOT EXISTS update_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_type TEXT NOT NULL,
    records_added INTEGER,
    duration_ms INTEGER,
    status TEXT,
    error_message TEXT
);

-- Greeks history for positions
CREATE TABLE IF NOT EXISTS greeks_history (
    timestamp DATETIME NOT NULL,
    position_type TEXT NOT NULL, -- 'strangle', 'call', 'put', 'spread'
    underlying TEXT NOT NULL DEFAULT 'SPY',
    call_strike REAL,
    put_strike REAL,
    expiry DATE NOT NULL,
    total_delta REAL,
    total_gamma REAL,
    total_theta REAL,
    total_vega REAL,
    total_rho REAL,
    underlying_price REAL,
    call_iv REAL,
    put_iv REAL,
    call_price REAL,
    put_price REAL,
    pnl REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (timestamp, position_type, expiry)
);

-- Index for fast Greeks queries
CREATE INDEX IF NOT EXISTS idx_greeks_timestamp ON greeks_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_greeks_expiry ON greeks_history(expiry);
CREATE INDEX IF NOT EXISTS idx_greeks_position ON greeks_history(position_type);

-- Cache statistics view
CREATE VIEW IF NOT EXISTS cache_stats AS
SELECT 
    (SELECT COUNT(*) FROM spy_prices) as total_spy_records,
    (SELECT COUNT(*) FROM options_data) as total_options_records,
    (SELECT MIN(timestamp) FROM spy_prices) as earliest_spy_data,
    (SELECT MAX(timestamp) FROM spy_prices) as latest_spy_data,
    (SELECT COUNT(DISTINCT date(timestamp)) FROM spy_prices) as trading_days_cached,
    (SELECT MAX(last_update) FROM data_status) as last_update_time;

-- Daily summary view for quick analysis
CREATE VIEW IF NOT EXISTS daily_summary AS
SELECT 
    date(timestamp) as trading_date,
    MIN(low) as daily_low,
    MAX(high) as daily_high,
    FIRST_VALUE(open) OVER (PARTITION BY date(timestamp) ORDER BY timestamp) as daily_open,
    LAST_VALUE(close) OVER (PARTITION BY date(timestamp) ORDER BY timestamp RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as daily_close,
    SUM(volume) as daily_volume,
    COUNT(*) as bar_count
FROM spy_prices
WHERE session_type = 'regular'
GROUP BY date(timestamp);