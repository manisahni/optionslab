# Changelog

All notable changes to the OptionsLab project will be documented in this file.

## [3.0.0] - 2025-09-03

### Added
- **Centralized Backtest Management System**: Complete infrastructure for managing backtests
  - Automatic storage organization by year/strategy/timestamp
  - Result indexing and search capabilities
  - Comparison tools for multiple strategies
  - Integration with notebooks and Gradio UI
  
- **Market Regime Detection**: EWMA-based volatility analysis
  - Three-regime classification (Low/Normal/High volatility)
  - Historical regime performance tracking
  - Major drawdown identification
  - Regime-filtered strategy configurations
  
- **Comprehensive Analysis Framework**: Multi-period testing
  - Mandatory test periods (2022 bear, 2023 recovery, etc.)
  - 5+ year dataset analysis (July 2020 - July 2025)
  - Automated performance comparison across periods
  
- **Enhanced Documentation**: Reorganized and expanded
  - Split oversized CLAUDE.md into focused documents
  - Created BACKTEST_USAGE_GUIDE.md for step-by-step instructions
  - Added backtests/README.md for system documentation
  - Updated SYSTEM_CAPABILITIES.md with latest features

### Changed
- Documentation structure reorganized for better memory management
- Increased dataset coverage to 1,266 trading days
- Enhanced backtest storage with automatic indexing
- Improved market filter integration with regime detection

### Technical
- Created `backtests/backtest_manager.py` for centralized management
- Added `backtests/market_regime_analyzer.py` for volatility analysis
- Implemented `backtests/run_comprehensive_analysis.py` for multi-period testing
- Built `backtests/gradio_results_viewer.py` for UI integration
- Added regime-filtered strategy configs (e.g., `long_call_regime_filtered.yaml`)

## [2.0.0] - 2025-07-23

### Added
- **OpenAI Integration**: Full AI assistant for trade analysis
  - Strategy adherence checking
  - Performance optimization suggestions
  - Natural language chat interface
  - Vision capabilities for chart analysis
  
- **Enhanced CSV Format**: Comprehensive trade logging
  - Complete metadata storage
  - Strategy configuration capture
  - Audit log inclusion
  - Excel-compatible format
  
- **Advanced Visualizations**: 13+ chart types
  - P&L curves with trade markers
  - Win/loss distributions
  - Monthly performance heatmaps
  - Greeks evolution tracking
  - Delta/DTE compliance charts
  - Exit efficiency analysis
  - Option coverage heatmaps
  - Technical indicators dashboard
  
- **Memorable Naming**: Unique names for backtests (e.g., "Swift Eagle-1423")
- **Unified Backtest Management**: Single selector across all tabs
- **AI Visualization Analysis**: AI-powered chart debugging and improvements

### Changed
- Migrated from port 7860 to 7862
- Updated startup script to `start_optionslab.sh`
- Improved modular architecture documentation
- Enhanced error handling throughout

### Fixed
- JSON serialization error with Timestamp objects
- Array comparison error in AI module (`pd.notna()`)
- Missing 'option_price' column in visualizations
- Trade log index synchronization issues

### Technical
- Added timestamp conversion in `csv_enhanced.py`
- Improved array handling in `ai_openai.py`
- Added column name flexibility in `visualization.py`
- Enhanced error messages and debugging

## [1.0.0] - 2025-07-01

### Initial Release
- Core backtesting engine
- Modular architecture
- Basic visualizations
- YAML strategy configuration
- Audit trail capability
- SPY options data support (2020-2025)
- Gradio web interface