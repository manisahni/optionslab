#!/usr/bin/env python
"""
Comprehensive Backtesting Script
Runs strategies across all market regimes and time periods
Stores results in centralized system for comparison
"""

import argparse
import json
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import sys
sys.path.append('/Users/nish_macbook/trading/daily-optionslab')

from backtests.backtest_manager import BacktestManager
from backtests.market_regime_analyzer import MarketRegimeAnalyzer


# Mandatory test periods as specified in CLAUDE.md
MANDATORY_PERIODS = [
    {"name": "Full Dataset", "start": "2020-07-15", "end": "2025-07-11", 
     "description": "Complete 5-year dataset covering all market conditions"},
    
    {"name": "2020 COVID Recovery", "start": "2020-07-15", "end": "2020-12-31",
     "description": "High volatility recovery period"},
    
    {"name": "2021 Bull Market", "start": "2021-01-01", "end": "2021-12-31",
     "description": "Low volatility bull market"},
    
    {"name": "2022 Bear Market", "start": "2022-01-01", "end": "2022-12-31",
     "description": "Extended -25% bear market with high volatility"},
    
    {"name": "2023 Recovery", "start": "2023-01-01", "end": "2023-12-31",
     "description": "Recovery period with multiple 10-15% corrections"},
    
    {"name": "2024 Bull Run", "start": "2024-01-01", "end": "2024-12-31",
     "description": "Strong bull market period"},
    
    {"name": "2025 Rate Volatility", "start": "2025-01-01", "end": "2025-07-11",
     "description": "Interest rate and tariff uncertainty period"}
]

# Specific drawdown periods to test
DRAWDOWN_PERIODS = [
    {"name": "2022 Q1 Drawdown", "start": "2022-02-01", "end": "2022-03-31",
     "description": "Initial 2022 correction"},
    
    {"name": "2022 Extended Bear", "start": "2022-04-01", "end": "2022-10-31",
     "description": "Main 2022 bear market"},
    
    {"name": "2023 Q3 Correction", "start": "2023-09-01", "end": "2023-10-31",
     "description": "2023 fall correction"}
]


class ComprehensiveBacktester:
    """Runs comprehensive backtesting across all periods and regimes"""
    
    def __init__(self, config_file: str, data_file: str = "data/spy_options/"):
        self.config_file = config_file
        self.data_file = data_file
        self.manager = BacktestManager()
        self.analyzer = MarketRegimeAnalyzer()
        self.results = []
        
    def run_all_periods(self, include_drawdowns: bool = True) -> pd.DataFrame:
        """Run backtests across all mandatory periods"""
        
        print("\n" + "="*60)
        print("COMPREHENSIVE BACKTESTING ANALYSIS")
        print("="*60)
        print(f"Strategy Config: {self.config_file}")
        print(f"Data Source: {self.data_file}")
        
        # Run mandatory periods
        print("\n📊 Testing Mandatory Periods...")
        for period in MANDATORY_PERIODS:
            print(f"\n▶️  {period['name']}: {period['start']} to {period['end']}")
            print(f"   {period['description']}")
            
            result = self.manager.run_backtest(
                config_file=self.config_file,
                start_date=period['start'],
                end_date=period['end'],
                data_file=self.data_file,
                description=f"{period['name']} - {period['description']}"
            )
            
            if result['success']:
                result['period_name'] = period['name']
                result['period_type'] = 'mandatory'
                self.results.append(result)
                
                # Display key metrics
                metrics = result.get('metrics', {})
                print(f"   ✅ Total Return: {metrics.get('total_return', 'N/A'):.2f}%")
                print(f"   📈 Sharpe Ratio: {metrics.get('sharpe_ratio', 'N/A'):.2f}")
                print(f"   📉 Max Drawdown: {metrics.get('max_drawdown', 'N/A'):.2f}%")
            else:
                print(f"   ❌ Backtest failed: {result.get('error', 'Unknown error')}")
        
        # Run drawdown periods if requested
        if include_drawdowns:
            print("\n📊 Testing Specific Drawdown Periods...")
            for period in DRAWDOWN_PERIODS:
                print(f"\n▶️  {period['name']}: {period['start']} to {period['end']}")
                
                result = self.manager.run_backtest(
                    config_file=self.config_file,
                    start_date=period['start'],
                    end_date=period['end'],
                    data_file=self.data_file,
                    description=f"{period['name']} - {period['description']}"
                )
                
                if result['success']:
                    result['period_name'] = period['name']
                    result['period_type'] = 'drawdown'
                    self.results.append(result)
                    
                    metrics = result.get('metrics', {})
                    print(f"   ✅ Total Return: {metrics.get('total_return', 'N/A'):.2f}%")
        
        # Create summary DataFrame
        summary_df = self._create_summary_dataframe()
        
        return summary_df
    
    def analyze_by_regime(self) -> pd.DataFrame:
        """Analyze performance by market regime"""
        
        print("\n📊 Analyzing Performance by Market Regime...")
        
        # Load market regime data
        self.analyzer.load_spy_prices("2020-07-15", "2025-07-11")
        self.analyzer.calculate_indicators()
        self.analyzer.identify_volatility_regimes()
        
        # Get regime summary
        regime_summary = self.analyzer.get_regime_summary()
        
        print("\n--- Market Regime Distribution ---")
        for regime, stats in regime_summary['volatility_regimes'].items():
            print(f"{regime}: {stats['days']} days ({stats['percentage']:.1f}%)")
        
        # Map results to regimes
        regime_performance = {}
        
        for result in self.results:
            period_name = result.get('period_name', '')
            metrics = result.get('metrics', {})
            
            # Classify period into regime
            if '2021' in period_name or 'Bull' in period_name:
                regime = 'low_vol_bull'
            elif '2022' in period_name or 'Bear' in period_name:
                regime = 'high_vol_bear'
            elif '2023' in period_name:
                regime = 'normal_vol_recovery'
            elif '2020' in period_name:
                regime = 'high_vol_recovery'
            elif '2025' in period_name:
                regime = 'rate_uncertainty'
            else:
                regime = 'mixed'
            
            if regime not in regime_performance:
                regime_performance[regime] = []
            
            regime_performance[regime].append({
                'period': period_name,
                'return': metrics.get('total_return', 0),
                'sharpe': metrics.get('sharpe_ratio', 0),
                'max_dd': metrics.get('max_drawdown', 0),
                'win_rate': metrics.get('win_rate', 0)
            })
        
        # Calculate average performance by regime
        print("\n--- Average Performance by Regime ---")
        for regime, results in regime_performance.items():
            if results:
                avg_return = np.mean([r['return'] for r in results])
                avg_sharpe = np.mean([r['sharpe'] for r in results if r['sharpe']])
                print(f"\n{regime}:")
                print(f"  Avg Return: {avg_return:.2f}%")
                print(f"  Avg Sharpe: {avg_sharpe:.2f}")
                print(f"  Periods tested: {len(results)}")
        
        return pd.DataFrame(regime_performance)
    
    def _create_summary_dataframe(self) -> pd.DataFrame:
        """Create summary DataFrame of all results"""
        
        summary_data = []
        
        for result in self.results:
            metrics = result.get('metrics', {})
            summary_data.append({
                'Period': result.get('period_name', 'Unknown'),
                'Type': result.get('period_type', 'Unknown'),
                'Result_ID': result.get('result_id', 'N/A'),
                'Total_Return_%': metrics.get('total_return', 0),
                'Sharpe_Ratio': metrics.get('sharpe_ratio', 0),
                'Max_Drawdown_%': metrics.get('max_drawdown', 0),
                'Win_Rate_%': metrics.get('win_rate', 0),
                'Total_Trades': metrics.get('total_trades', 0)
            })
        
        df = pd.DataFrame(summary_data)
        
        # Sort by total return
        df = df.sort_values('Total_Return_%', ascending=False)
        
        return df
    
    def generate_report(self, output_file: str = None) -> str:
        """Generate comprehensive analysis report"""
        
        if not self.results:
            return "No results to report"
        
        report = []
        report.append("\n" + "="*60)
        report.append("COMPREHENSIVE BACKTEST REPORT")
        report.append("="*60)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Strategy: {self.config_file}")
        report.append(f"Total Periods Tested: {len(self.results)}")
        
        # Summary statistics
        all_returns = [r.get('metrics', {}).get('total_return', 0) for r in self.results]
        report.append(f"\n--- Overall Statistics ---")
        report.append(f"Average Return: {np.mean(all_returns):.2f}%")
        report.append(f"Best Period Return: {np.max(all_returns):.2f}%")
        report.append(f"Worst Period Return: {np.min(all_returns):.2f}%")
        report.append(f"Return Std Dev: {np.std(all_returns):.2f}%")
        
        # Best and worst periods
        best_idx = np.argmax(all_returns)
        worst_idx = np.argmin(all_returns)
        
        report.append(f"\n--- Best Period ---")
        report.append(f"Period: {self.results[best_idx].get('period_name', 'Unknown')}")
        report.append(f"Return: {all_returns[best_idx]:.2f}%")
        
        report.append(f"\n--- Worst Period ---")
        report.append(f"Period: {self.results[worst_idx].get('period_name', 'Unknown')}")
        report.append(f"Return: {all_returns[worst_idx]:.2f}%")
        
        # Detailed results
        report.append(f"\n--- Detailed Results by Period ---")
        summary_df = self._create_summary_dataframe()
        report.append(summary_df.to_string())
        
        # Recommendations
        report.append(f"\n--- Strategy Recommendations ---")
        
        # Check bear market performance
        bear_results = [r for r in self.results if '2022' in r.get('period_name', '')]
        if bear_results:
            bear_return = bear_results[0].get('metrics', {}).get('total_return', 0)
            if bear_return < -20:
                report.append("⚠️  Strategy performs poorly in bear markets - consider defensive filters")
            elif bear_return > 0:
                report.append("✅ Strategy shows resilience in bear markets")
        
        # Check volatility sensitivity
        high_vol_results = [r for r in self.results if any(x in r.get('period_name', '') 
                           for x in ['2020', '2022', '2025'])]
        low_vol_results = [r for r in self.results if '2021' in r.get('period_name', '')]
        
        if high_vol_results and low_vol_results:
            high_vol_avg = np.mean([r.get('metrics', {}).get('total_return', 0) 
                                   for r in high_vol_results])
            low_vol_avg = np.mean([r.get('metrics', {}).get('total_return', 0) 
                                  for r in low_vol_results])
            
            if high_vol_avg > low_vol_avg * 1.5:
                report.append("📈 Strategy performs better in high volatility - long options bias")
            elif low_vol_avg > high_vol_avg * 1.5:
                report.append("📉 Strategy performs better in low volatility - short options bias")
        
        # Save report
        report_text = '\n'.join(report)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
            print(f"\n✅ Report saved to: {output_file}")
        
        return report_text
    
    def export_results(self, filepath: str = None):
        """Export all results to CSV"""
        
        if not filepath:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = f"backtests/results/comprehensive_analysis_{timestamp}.csv"
        
        summary_df = self._create_summary_dataframe()
        summary_df.to_csv(filepath, index=False)
        
        print(f"\n✅ Results exported to: {filepath}")
        
        return filepath


def main():
    """Main entry point for comprehensive backtesting"""
    
    parser = argparse.ArgumentParser(description="Run comprehensive backtest analysis")
    parser.add_argument("--config", required=True, help="Strategy config file")
    parser.add_argument("--data", default="data/spy_options/", help="Data directory")
    parser.add_argument("--analyze-regimes", action="store_true", 
                       help="Analyze performance by market regime")
    parser.add_argument("--compare-periods", action="store_true",
                       help="Compare performance across periods")
    parser.add_argument("--skip-drawdowns", action="store_true",
                       help="Skip specific drawdown period tests")
    parser.add_argument("--output", help="Output report file")
    
    args = parser.parse_args()
    
    # Initialize backtester
    backtester = ComprehensiveBacktester(args.config, args.data)
    
    # Run comprehensive analysis
    summary_df = backtester.run_all_periods(include_drawdowns=not args.skip_drawdowns)
    
    # Analyze by regime if requested
    if args.analyze_regimes:
        backtester.analyze_by_regime()
    
    # Generate report
    report = backtester.generate_report(args.output)
    print(report)
    
    # Export results
    backtester.export_results()
    
    # Display summary
    print("\n" + "="*60)
    print("ANALYSIS COMPLETE")
    print("="*60)
    print(f"Total backtests run: {len(backtester.results)}")
    print(f"Results stored in centralized system")
    print("\nSummary Table:")
    print(summary_df.to_string())


if __name__ == "__main__":
    # Example usage without command line args
    import sys
    
    if len(sys.argv) == 1:
        # Default test with long_call_simple
        print("Running default comprehensive analysis with long_call_simple...")
        
        backtester = ComprehensiveBacktester(
            config_file="config/long_call_simple.yaml",
            data_file="data/spy_options/"
        )
        
        # Run all periods
        summary_df = backtester.run_all_periods(include_drawdowns=False)
        
        # Analyze by regime
        backtester.analyze_by_regime()
        
        # Generate report
        report = backtester.generate_report("backtests/results/comprehensive_report.txt")
        
        # Export results
        backtester.export_results()
    else:
        main()