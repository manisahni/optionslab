# 🔒 PROTECTED FILES - CORE BACKTESTING INFRASTRUCTURE

## ⛔ CRITICAL: NO MODIFICATIONS WITHOUT EXPLICIT PERMISSION

These files represent hundreds of hours of development and testing. They are the proven, stable foundation of the entire options backtesting system. **ANY modification requires user to explicitly state: "modify optionslab/[filename]"**

## Core Backtesting Engine (ABSOLUTELY PROTECTED)
```
optionslab/
├── backtest_engine.py      # ⛔ Main orchestration - DO NOT MODIFY
├── option_selector.py      # ⛔ Option selection logic - DO NOT MODIFY  
├── greek_tracker.py        # ⛔ Greeks tracking system - DO NOT MODIFY
├── trade_recorder.py       # ⛔ Trade recording/audit - DO NOT MODIFY
├── market_filters.py       # ⛔ Market conditions - DO NOT MODIFY
├── exit_conditions.py      # ⛔ Exit logic - DO NOT MODIFY
├── backtest_metrics.py     # ⛔ Performance calcs - DO NOT MODIFY
└── data_loader.py          # ⛔ Data loading (stable) - DO NOT MODIFY
```

## Visualization & Reporting (PROTECTED)
```
optionslab/
├── visualization.py        # ⛔ Chart generation - DO NOT MODIFY
├── csv_enhanced.py         # ⛔ Trade logging - DO NOT MODIFY
└── visualization_utils.py  # ⛔ Viz helpers - DO NOT MODIFY
```

## Application Layer (PROTECTED)
```
optionslab/
└── app.py                  # ⛔ Main Gradio UI - DO NOT MODIFY
```

## Data Infrastructure (PROTECTED)
```
├── thetadata_client/       # ⛔ ThetaData API client - DO NOT MODIFY
├── data/spy_options/       # ⛔ 1,265 EOD files - NEVER DELETE/OVERWRITE
└── spy_options_downloader/ # ⛔ Download infrastructure - DO NOT MODIFY
```

## ✅ Files That CAN Be Modified (with care)
```
├── optionslab/multi_leg_selector.py  # New/experimental - can modify
├── optionslab/thetadata_loader.py    # Data interface - can modify carefully
├── config/*.yaml                      # Strategy configs - modify freely
├── notebooks/research/                # Research - modify freely
└── notebooks/strategies/              # Strategy development - modify freely
```

## 🛡️ Why This Protection Is Critical

1. **Proven Stability**: These modules have been tested with thousands of backtests
2. **Complex Dependencies**: Changes can cascade and break everything
3. **Validated Logic**: Core calculations match real broker execution
4. **Historical Consistency**: Modifications invalidate all previous results
5. **Time Investment**: Hundreds of hours of debugging and refinement

## 📝 Rules for Any Modifications

**BEFORE modifying ANY protected file:**
1. ❌ User MUST explicitly request: "modify optionslab/[filename]"
2. ❌ Document EXACTLY what will change and why
3. ❌ Explain why existing functionality doesn't work
4. ❌ Test that ALL existing strategies still function
5. ❌ Create fallback plan if changes break something

**NEVER modify protected files for:**
- Adding new strategies → Use config YAML files instead
- Custom analysis → Use research notebooks instead  
- Data experiments → Create new notebooks instead
- UI changes → Discuss architecture first

## 🎯 Where to Make Changes Instead

| Need | Don't Modify | Do This Instead |
|------|--------------|-----------------|
| New strategy | backtest_engine.py | Create new YAML in config/ |
| Custom analysis | visualization.py | Create notebook in research/ |
| Different data | data_loader.py | Load in notebook with custom code |
| New metrics | backtest_metrics.py | Calculate in notebook post-backtest |
| UI features | app.py | Discuss requirements first |