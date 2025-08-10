#!/usr/bin/env python3
"""Greeks validation tool to check theoretical relationships and data quality"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class GreeksValidationResult:
    """Results from Greeks validation"""
    passed: bool
    score: float  # 0-100
    issues: List[str]
    warnings: List[str]
    statistics: Dict[str, float]


class GreeksValidator:
    """Validate option Greeks for theoretical consistency"""
    
    def __init__(self, tolerance: float = 0.1):
        """
        Initialize validator
        
        Args:
            tolerance: Relative tolerance for checks (default 10%)
        """
        self.tolerance = tolerance
    
    def validate_options_data(self, df: pd.DataFrame, 
                            option_type: Optional[str] = None) -> GreeksValidationResult:
        """
        Validate Greeks in options data
        
        Args:
            df: DataFrame with options data
            option_type: Optional filter for 'CALL' or 'PUT'
            
        Returns:
            GreeksValidationResult with findings
        """
        issues = []
        warnings = []
        stats = {}
        
        # Filter by option type if specified
        if option_type:
            df = df[df['right'] == option_type].copy()
        
        if len(df) == 0:
            return GreeksValidationResult(
                passed=False,
                score=0,
                issues=["No data to validate"],
                warnings=[],
                statistics={}
            )
        
        # Get underlying price
        spy_price = df.iloc[0].get('underlying_price_dollar', 
                                   df.iloc[0].get('underlying_price', 0) / 100)
        
        # Run validation checks
        checks_passed = 0
        total_checks = 0
        
        # 1. Delta checks
        delta_result = self._validate_delta(df, spy_price)
        checks_passed += delta_result['passed']
        total_checks += 1
        issues.extend(delta_result['issues'])
        warnings.extend(delta_result['warnings'])
        stats.update(delta_result['stats'])
        
        # 2. Gamma checks
        if 'gamma' in df.columns:
            gamma_result = self._validate_gamma(df, spy_price)
            checks_passed += gamma_result['passed']
            total_checks += 1
            issues.extend(gamma_result['issues'])
            warnings.extend(gamma_result['warnings'])
            stats.update(gamma_result['stats'])
        else:
            issues.append("Gamma is missing from dataset")
        
        # 3. Theta checks
        if 'theta' in df.columns:
            theta_result = self._validate_theta(df, spy_price)
            checks_passed += theta_result['passed']
            total_checks += 1
            issues.extend(theta_result['issues'])
            warnings.extend(theta_result['warnings'])
            stats.update(theta_result['stats'])
        
        # 4. Vega checks
        if 'vega' in df.columns:
            vega_result = self._validate_vega(df, spy_price)
            checks_passed += vega_result['passed']
            total_checks += 1
            issues.extend(vega_result['issues'])
            warnings.extend(vega_result['warnings'])
            stats.update(vega_result['stats'])
        
        # 5. Cross-Greek relationships
        relationship_result = self._validate_relationships(df, spy_price)
        checks_passed += relationship_result['passed']
        total_checks += 1
        issues.extend(relationship_result['issues'])
        warnings.extend(relationship_result['warnings'])
        
        # Calculate overall score
        score = (checks_passed / total_checks * 100) if total_checks > 0 else 0
        
        return GreeksValidationResult(
            passed=len(issues) == 0,
            score=score,
            issues=issues,
            warnings=warnings,
            statistics=stats
        )
    
    def _validate_delta(self, df: pd.DataFrame, spy_price: float) -> Dict:
        """Validate delta values"""
        issues = []
        warnings = []
        stats = {}
        
        calls = df[df['right'] == 'CALL']
        puts = df[df['right'] == 'PUT']
        
        # Check call deltas
        if len(calls) > 0:
            # No call should have delta > 1 or < 0
            invalid_call_deltas = calls[(calls['delta'] > 1) | (calls['delta'] < 0)]
            if len(invalid_call_deltas) > 0:
                issues.append(f"{len(invalid_call_deltas)} calls have invalid delta (outside 0-1)")
            
            # Check for constant delta = 1
            delta_1_calls = calls[calls['delta'] == 1.0]
            otm_delta_1 = delta_1_calls[delta_1_calls['strike'] > spy_price]
            if len(otm_delta_1) > 0:
                issues.append(f"{len(otm_delta_1)} OTM calls have delta = 1.0 (impossible)")
            
            # Check monotonicity
            sorted_calls = calls.sort_values('strike')
            if len(sorted_calls) > 1:
                delta_increases = (sorted_calls['delta'].diff() > 0).sum()
                if delta_increases > len(sorted_calls) * 0.1:  # Allow 10% anomalies
                    warnings.append(f"Call delta not monotonically decreasing ({delta_increases} increases)")
            
            stats['call_delta_mean'] = calls['delta'].mean()
            stats['call_delta_std'] = calls['delta'].std()
        
        # Check put deltas
        if len(puts) > 0:
            # Put deltas should be between -1 and 0
            invalid_put_deltas = puts[(puts['delta'] > 0) | (puts['delta'] < -1)]
            if len(invalid_put_deltas) > 0:
                issues.append(f"{len(invalid_put_deltas)} puts have invalid delta (outside -1 to 0)")
            
            stats['put_delta_mean'] = puts['delta'].mean()
        
        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'stats': stats
        }
    
    def _validate_gamma(self, df: pd.DataFrame, spy_price: float) -> Dict:
        """Validate gamma values"""
        issues = []
        warnings = []
        stats = {}
        
        # Gamma should always be positive
        negative_gamma = df[df['gamma'] < 0]
        if len(negative_gamma) > 0:
            issues.append(f"{len(negative_gamma)} options have negative gamma (should be positive)")
        
        # Find where gamma is maximum
        if not df['gamma'].isna().all():
            max_gamma_idx = df['gamma'].idxmax()
            max_gamma_strike = df.loc[max_gamma_idx, 'strike']
            
            # Should be near ATM
            atm_distance = abs(max_gamma_strike - spy_price)
            if atm_distance > spy_price * 0.02:  # More than 2% away
                warnings.append(f"Maximum gamma at ${max_gamma_strike} is {atm_distance/spy_price*100:.1f}% from ATM")
            
            stats['max_gamma'] = df['gamma'].max()
            stats['max_gamma_strike'] = max_gamma_strike
            stats['gamma_mean'] = df['gamma'].mean()
        
        # Check for too many zero gammas
        zero_gamma = df[df['gamma'] == 0]
        if len(zero_gamma) > len(df) * 0.5:
            warnings.append(f"{len(zero_gamma)/len(df)*100:.1f}% of options have gamma = 0")
        
        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'stats': stats
        }
    
    def _validate_theta(self, df: pd.DataFrame, spy_price: float) -> Dict:
        """Validate theta values"""
        issues = []
        warnings = []
        stats = {}
        
        # For 0DTE, theta should be negative (time decay)
        positive_theta = df[df['theta'] > 0]
        if len(positive_theta) > 0:
            issues.append(f"{len(positive_theta)} options have positive theta (should be negative)")
        
        # Check for too many zero thetas
        zero_theta = df[df['theta'] == 0]
        if len(zero_theta) > len(df) * 0.3:  # More than 30%
            issues.append(f"{len(zero_theta)/len(df)*100:.1f}% of options have theta = 0 (suspicious for 0DTE)")
        
        # Theta should be most negative near ATM
        if not df['theta'].isna().all() and df['theta'].min() < 0:
            min_theta_idx = df['theta'].idxmin()  # Most negative
            min_theta_strike = df.loc[min_theta_idx, 'strike']
            
            atm_distance = abs(min_theta_strike - spy_price)
            if atm_distance > spy_price * 0.02:
                warnings.append(f"Most negative theta at ${min_theta_strike} is {atm_distance/spy_price*100:.1f}% from ATM")
            
            stats['theta_mean'] = df['theta'].mean()
            stats['theta_min'] = df['theta'].min()
            stats['min_theta_strike'] = min_theta_strike
        
        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'stats': stats
        }
    
    def _validate_vega(self, df: pd.DataFrame, spy_price: float) -> Dict:
        """Validate vega values"""
        issues = []
        warnings = []
        stats = {}
        
        # Vega should be positive
        negative_vega = df[df['vega'] < 0]
        if len(negative_vega) > 0:
            issues.append(f"{len(negative_vega)} options have negative vega (should be positive)")
        
        # Check for too many zero vegas
        zero_vega = df[df['vega'] == 0]
        if len(zero_vega) > len(df) * 0.5:
            warnings.append(f"{len(zero_vega)/len(df)*100:.1f}% of options have vega = 0")
        
        # Vega should be highest near ATM
        if not df['vega'].isna().all() and df['vega'].max() > 0:
            max_vega_idx = df['vega'].idxmax()
            max_vega_strike = df.loc[max_vega_idx, 'strike']
            
            atm_distance = abs(max_vega_strike - spy_price)
            if atm_distance > spy_price * 0.02:
                warnings.append(f"Maximum vega at ${max_vega_strike} is {atm_distance/spy_price*100:.1f}% from ATM")
            
            stats['vega_mean'] = df['vega'].mean()
            stats['vega_max'] = df['vega'].max()
        
        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'stats': stats
        }
    
    def _validate_relationships(self, df: pd.DataFrame, spy_price: float) -> Dict:
        """Validate cross-Greek relationships"""
        issues = []
        warnings = []
        
        # Check if gamma and vega peak at similar strikes
        if 'gamma' in df.columns and 'vega' in df.columns:
            if not df['gamma'].isna().all() and not df['vega'].isna().all():
                max_gamma_strike = df.loc[df['gamma'].idxmax(), 'strike']
                max_vega_strike = df.loc[df['vega'].idxmax(), 'strike']
                
                if abs(max_gamma_strike - max_vega_strike) > spy_price * 0.01:
                    warnings.append(f"Gamma and vega peak at different strikes (${max_gamma_strike} vs ${max_vega_strike})")
        
        # Check delta-gamma relationship
        if 'gamma' in df.columns:
            # Near 0.5 delta should have high gamma
            mid_delta = df[(df['delta'] > 0.4) & (df['delta'] < 0.6)]
            if len(mid_delta) > 0 and not mid_delta['gamma'].isna().all():
                avg_mid_gamma = mid_delta['gamma'].mean()
                overall_avg_gamma = df['gamma'].mean()
                
                if avg_mid_gamma < overall_avg_gamma:
                    warnings.append("Gamma not highest at mid-delta range (0.4-0.6)")
        
        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }
    
    def generate_report(self, df: pd.DataFrame) -> str:
        """Generate a text report of validation results"""
        report = []
        report.append("="*80)
        report.append("GREEKS VALIDATION REPORT")
        report.append("="*80)
        
        # Validate calls
        report.append("\nCALL OPTIONS:")
        report.append("-"*40)
        call_result = self.validate_options_data(df, 'CALL')
        report.append(f"Score: {call_result.score:.1f}/100")
        report.append(f"Passed: {'YES' if call_result.passed else 'NO'}")
        
        if call_result.issues:
            report.append("\nIssues:")
            for issue in call_result.issues:
                report.append(f"  ❌ {issue}")
        
        if call_result.warnings:
            report.append("\nWarnings:")
            for warning in call_result.warnings:
                report.append(f"  ⚠️  {warning}")
        
        # Validate puts
        report.append("\n\nPUT OPTIONS:")
        report.append("-"*40)
        put_result = self.validate_options_data(df, 'PUT')
        report.append(f"Score: {put_result.score:.1f}/100")
        report.append(f"Passed: {'YES' if put_result.passed else 'NO'}")
        
        if put_result.issues:
            report.append("\nIssues:")
            for issue in put_result.issues:
                report.append(f"  ❌ {issue}")
        
        # Overall summary
        report.append("\n" + "="*80)
        report.append("SUMMARY")
        report.append("="*80)
        
        overall_score = (call_result.score + put_result.score) / 2
        report.append(f"Overall Score: {overall_score:.1f}/100")
        report.append(f"Overall Result: {'PASS' if call_result.passed and put_result.passed else 'FAIL'}")
        
        # Key statistics
        if call_result.statistics:
            report.append("\nKey Statistics:")
            for key, value in call_result.statistics.items():
                if isinstance(value, float):
                    report.append(f"  {key}: {value:.4f}")
                else:
                    report.append(f"  {key}: {value}")
        
        return "\n".join(report)


if __name__ == "__main__":
    # Test the validator
    import sys
    sys.path.append('..')
    from zero_dte_spy_options_database import MinuteLevelOptionsDatabase
    from black_scholes_calculator import BlackScholesCalculator
    
    # Load and validate original data
    db = MinuteLevelOptionsDatabase()
    df = db.load_zero_dte_data('20250728')
    time_10am = df[df['timestamp'] == '2025-07-28T10:00:00'].copy()
    
    validator = GreeksValidator()
    
    print("VALIDATING ORIGINAL DATA")
    print("="*80)
    result = validator.validate_options_data(time_10am)
    print(validator.generate_report(time_10am))
    
    # Now validate corrected data
    print("\n\n")
    print("VALIDATING CORRECTED DATA")
    print("="*80)
    
    calculator = BlackScholesCalculator()
    corrected = calculator.correct_options_data(time_10am)
    
    result = validator.validate_options_data(corrected)
    print(validator.generate_report(corrected))