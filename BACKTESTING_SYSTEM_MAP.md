# 🗺️ OptionsLab Backtesting System Map

## 📁 File Structure & Data Flow

```
thetadata-api/
├── 🎯 CORE BACKTESTING ENGINE
│   ├── backtest_engine.py          # 🧠 Main backtesting logic
│   │   ├── run_backtest()          # Core backtest function
│   │   ├── load_spy_data()         # Market data loading
│   │   ├── calculate_option_price() # Option pricing (simplified)
│   │   └── plot_results()          # Visualization
│   │
│   └── config/strategies/          # 📋 Strategy configurations
│       ├── simple_long_call.yaml   # YAML strategy files
│       ├── simple_long_put.yaml
│       ├── simple_csp.yaml
│       └── ... (7 total strategies)
│
├── 🌐 API LAYER
│   ├── backend.py                  # 🚀 FastAPI server
│   │   ├── /backtest              # POST endpoint
│   │   ├── /strategies            # GET available strategies
│   │   ├── /ai/status             # AI system status
│   │   ├── /ai/generate-strategy  # AI strategy generation
│   │   └── /ai/analyze-backtest   # AI analysis
│   │
│   └── simple_ai_system.py        # 🤖 AI integration
│       ├── GeminiClient           # Google Gemini API
│       ├── StrategyAnalyzer       # Strategy analysis
│       └── ChatAssistant          # AI chat interface
│
├── 🖥️ FRONTEND LAYER
│   └── simple_gradio_app.py       # 🎨 Gradio UI
│       ├── create_interface()     # UI components
│       ├── run_backtest()         # API calls
│       ├── generate_ai_strategy() # AI integration
│       └── format_results()       # Results display
│
└── 📊 DATA & RESULTS
    ├── results/                   # Backtest results storage
    ├── logs/                      # System logs
    └── *.png                      # Generated plots
```

## 🔄 Data Flow Architecture

### **1. User Input Flow**
```
User (Gradio UI) 
    ↓
simple_gradio_app.py
    ↓ (HTTP Request)
backend.py (/backtest endpoint)
    ↓
backtest_engine.py (run_backtest function)
    ↓
Results returned to UI
```

### **2. Strategy Configuration Flow**
```
YAML Files (config/strategies/)
    ↓
AI System (simple_ai_system.py)
    ↓
Strategy Generation/Modification
    ↓
Save back to YAML or use directly
```

### **3. AI Integration Flow**
```
User Request (AI features)
    ↓
Gradio UI (AI tabs)
    ↓
FastAPI (/ai/* endpoints)
    ↓
simple_ai_system.py (Gemini integration)
    ↓
AI Analysis/Generation
    ↓
Results back to UI
```

## 🧠 Core Functions Breakdown

### **backtest_engine.py - The Brain**
```python
# Main entry point
def run_backtest(strategy_type, start_date, end_date, initial_capital):
    """
    🎯 CORE FUNCTION: Orchestrates entire backtest
    - Loads market data
    - Executes strategy logic
    - Tracks positions and P&L
    - Returns comprehensive results
    """

# Data loading
def load_spy_data(start_date, end_date):
    """
    📈 MARKET DATA: Currently generates synthetic data
    - Creates SPY price series
    - Simulates market movements
    - Returns pandas DataFrame
    """

# Option pricing
def calculate_option_price(spot_price, strike, time_to_expiry, volatility, risk_free_rate, option_type):
    """
    💰 OPTION PRICING: Simplified Black-Scholes
    - Calculates option values
    - Handles calls and puts
    - Used for P&L calculations
    """

# Visualization
def plot_results(results, save_path=None):
    """
    📊 VISUALIZATION: Creates performance charts
    - Equity curves
    - Trade analysis
    - Performance metrics
    """
```

### **backend.py - The API Gateway**
```python
# Main backtest endpoint
@app.post("/backtest")
async def run_backtest_api(request: BacktestRequest):
    """
    🌐 API ENDPOINT: Receives requests from frontend
    - Validates input parameters
    - Calls backtest_engine.run_backtest()
    - Returns JSON response with results
    """

# AI integration endpoints
@app.post("/ai/generate-strategy")
@app.post("/ai/analyze-backtest")
@app.get("/ai/status")
```

### **simple_gradio_app.py - The User Interface**
```python
# Main UI function
def create_interface():
    """
    🎨 UI CREATION: Builds Gradio interface
    - Input forms for backtest parameters
    - AI strategy generation interface
    - Results display and visualization
    """

# API communication
def run_backtest(strategy, start_date, end_date, initial_capital):
    """
    🔗 API CALLS: Communicates with backend
    - Sends HTTP requests to FastAPI
    - Handles responses and errors
    - Formats results for display
    """
```

## 📊 Data Structures

### **Backtest Results Structure**
```python
{
    "performance_metrics": {
        "initial_capital": 10000,
        "final_value": 11500,
        "total_return": 0.15,
        "win_rate": 0.65,
        "max_drawdown": -0.08,
        "sharpe_ratio": 1.2
    },
    "equity_curve": [
        {
            "date": "2024-01-01",
            "cash": 9500,
            "total_value": 10000,
            "positions": 1
        }
    ],
    "trade_logs": [
        {
            "entry_date": "2024-01-01",
            "exit_date": "2024-01-06",
            "option_type": "call",
            "strike": 459.0,
            "quantity": 2,
            "entry_price": 2.50,
            "exit_price": 3.75,
            "pnl": 250.0,
            "exit_reason": "time_exit"
        }
    ]
}
```

### **YAML Strategy Structure**
```yaml
name: "Simple Long Call"
description: "Buy calls expecting price to go up"
category: "directional"

legs:
  - type: call
    direction: long
    quantity: 1
    delta_target: 0.40

entry_rules:
  dte: 30
  delta_target: 0.40
  volume_min: 100
  open_interest_min: 500

exit_rules:
  profit_target_pct: 0.50
  stop_loss_pct: 0.50
  exit_on_dte: 7

risk_management:
  max_positions: 2
  position_sizing: "fixed"
  max_position_size: 0.05
```

## 🔧 Current Implementation Status

### **✅ What's Working:**
1. **Core Backtesting Engine**: Fully functional with synthetic data
2. **API Layer**: FastAPI server with all endpoints
3. **Frontend**: Gradio UI with backtest and AI features
4. **Strategy Configuration**: YAML-based strategy definitions
5. **AI Integration**: Gemini API integration for analysis

### **🔄 Data Sources:**
- **Current**: Synthetic SPY data generation
- **Future**: Real market data from parquet files
- **AI**: Google Gemini API for strategy analysis

### **📈 Performance Tracking:**
- Equity curve calculation
- Trade-by-trade P&L
- Risk metrics (drawdown, Sharpe ratio)
- Win rate analysis

## 🎯 Key Integration Points

### **1. Strategy Loading**
```python
# YAML → Python → Backtest
yaml_config = load_yaml("config/strategies/simple_long_call.yaml")
strategy_params = parse_yaml_config(yaml_config)
results = run_backtest(strategy_params)
```

### **2. AI Analysis**
```python
# Backtest Results → AI → Analysis
backtest_results = run_backtest(...)
ai_analysis = ai_system.analyze_backtest(backtest_results)
```

### **3. Visualization**
```python
# Results → Plots → UI
results = run_backtest(...)
plots = plot_results(results)
display_in_ui(plots)
```

## 🚀 Future Enhancements

### **Phase 1: Real Data Integration**
- Replace synthetic data with real SPY options data
- Load from parquet files in `spy_options_downloader/`
- Implement proper options pricing models

### **Phase 2: Advanced Strategies**
- Multi-leg options strategies
- Dynamic position sizing
- Advanced risk management

### **Phase 3: AI Enhancement**
- AI can read and modify backtest_engine.py
- AI can generate and validate YAML files
- AI can suggest strategy improvements

---

## 📝 Summary

The backtesting system is built with a **clean separation of concerns**:

- **`backtest_engine.py`**: Core backtesting logic (the brain)
- **`backend.py`**: API layer for communication
- **`simple_gradio_app.py`**: User interface
- **`config/strategies/`**: Strategy configurations
- **`simple_ai_system.py`**: AI integration

The system supports **multiple interfaces** (YAML, CLI, Python) and provides **AI-powered analysis** while maintaining a **modular, extensible architecture**. 