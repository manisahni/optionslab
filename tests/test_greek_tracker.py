#!/usr/bin/env python3
"""
Tests for the Greek tracker module
"""

import pytest
from optionslab.greek_tracker import GreekTracker, GreekSnapshot


def test_greek_snapshot_creation():
    """Test creating Greek snapshots"""
    snapshot = GreekSnapshot(
        delta=0.5,
        gamma=0.02,
        theta=-0.05,
        vega=0.15,
        iv=0.25,
        underlying_price=450.0,
        option_price=5.50,
        dte=45
    )
    
    assert snapshot.delta == 0.5
    assert snapshot.gamma == 0.02
    assert snapshot.theta == -0.05
    assert snapshot.vega == 0.15
    assert snapshot.iv == 0.25
    assert snapshot.underlying_price == 450.0
    assert snapshot.option_price == 5.50
    assert snapshot.dte == 45


def test_greek_tracker_initialization():
    """Test Greek tracker initialization"""
    entry_snapshot = GreekSnapshot(
        delta=0.5,
        gamma=0.02,
        theta=-0.05,
        vega=0.15,
        iv=0.25,
        underlying_price=450.0,
        option_price=5.50,
        dte=45
    )
    
    tracker = GreekTracker(entry_greeks=entry_snapshot)
    
    assert tracker.entry_greeks == entry_snapshot
    assert tracker.current_greeks is None
    assert tracker.exit_greeks is None


def test_greek_tracker_update():
    """Test updating Greek tracker with current values"""
    # Create entry snapshot
    entry_snapshot = GreekSnapshot(
        delta=0.5,
        gamma=0.02,
        theta=-0.05,
        vega=0.15,
        iv=0.25,
        underlying_price=450.0,
        option_price=5.50,
        dte=45
    )
    
    tracker = GreekTracker(entry_greeks=entry_snapshot)
    
    # Update with current values
    current_snapshot = GreekSnapshot(
        delta=0.6,  # Delta increased as option moved ITM
        gamma=0.018,
        theta=-0.06,
        vega=0.14,
        iv=0.24,
        underlying_price=455.0,  # Price moved up
        option_price=7.00,       # Option value increased
        dte=40                   # 5 days passed
    )
    
    tracker.current_greeks = current_snapshot
    
    # Verify updates
    assert tracker.current_greeks.delta == 0.6
    assert tracker.current_greeks.underlying_price == 455.0
    assert tracker.current_greeks.option_price == 7.00
    assert tracker.current_greeks.dte == 40


def test_greek_tracker_exit():
    """Test recording exit Greeks"""
    # Create full lifecycle
    entry_snapshot = GreekSnapshot(
        delta=0.5, gamma=0.02, theta=-0.05, vega=0.15,
        iv=0.25, underlying_price=450.0, option_price=5.50, dte=45
    )
    
    tracker = GreekTracker(entry_greeks=entry_snapshot)
    
    # Record exit
    exit_snapshot = GreekSnapshot(
        delta=0.7, gamma=0.015, theta=-0.08, vega=0.12,
        iv=0.22, underlying_price=460.0, option_price=10.50, dte=30
    )
    
    tracker.exit_greeks = exit_snapshot
    
    # Verify complete lifecycle is tracked
    assert tracker.entry_greeks.delta == 0.5
    assert tracker.exit_greeks.delta == 0.7
    assert tracker.exit_greeks.option_price == 10.50


def test_greek_changes_calculation():
    """Test calculating Greek changes over position lifetime"""
    entry_snapshot = GreekSnapshot(
        delta=0.5, gamma=0.02, theta=-0.05, vega=0.15,
        iv=0.25, underlying_price=450.0, option_price=5.50, dte=45
    )
    
    exit_snapshot = GreekSnapshot(
        delta=0.7, gamma=0.015, theta=-0.08, vega=0.12,
        iv=0.22, underlying_price=460.0, option_price=10.50, dte=30
    )
    
    tracker = GreekTracker(entry_greeks=entry_snapshot)
    tracker.exit_greeks = exit_snapshot
    
    # Calculate changes
    delta_change = tracker.exit_greeks.delta - tracker.entry_greeks.delta
    price_change = tracker.exit_greeks.underlying_price - tracker.entry_greeks.underlying_price
    option_pnl = tracker.exit_greeks.option_price - tracker.entry_greeks.option_price
    
    assert delta_change == 0.2  # Delta increased by 0.2
    assert price_change == 10.0  # Underlying moved $10
    assert option_pnl == 5.0     # Option gained $5


def test_greek_tracker_portfolio_aggregation():
    """Test aggregating Greeks across multiple positions"""
    # Create multiple trackers for portfolio
    tracker1 = GreekTracker(
        entry_greeks=GreekSnapshot(
            delta=0.5, gamma=0.02, theta=-0.05, vega=0.15,
            iv=0.25, underlying_price=450.0, option_price=5.50, dte=45
        )
    )
    
    tracker2 = GreekTracker(
        entry_greeks=GreekSnapshot(
            delta=0.4, gamma=0.025, theta=-0.04, vega=0.18,
            iv=0.26, underlying_price=450.0, option_price=4.00, dte=60
        )
    )
    
    # Portfolio Greeks would be sum of individual positions
    portfolio_delta = tracker1.entry_greeks.delta + tracker2.entry_greeks.delta
    portfolio_gamma = tracker1.entry_greeks.gamma + tracker2.entry_greeks.gamma
    portfolio_theta = tracker1.entry_greeks.theta + tracker2.entry_greeks.theta
    portfolio_vega = tracker1.entry_greeks.vega + tracker2.entry_greeks.vega
    
    assert portfolio_delta == 0.9
    assert portfolio_gamma == 0.045
    assert portfolio_theta == -0.09
    assert portfolio_vega == 0.33


def test_greek_tracker_serialization():
    """Test Greek tracker can be serialized for storage"""
    entry_snapshot = GreekSnapshot(
        delta=0.5, gamma=0.02, theta=-0.05, vega=0.15,
        iv=0.25, underlying_price=450.0, option_price=5.50, dte=45
    )
    
    tracker = GreekTracker(entry_greeks=entry_snapshot)
    
    # Convert to dict for storage
    tracker_dict = {
        'entry_greeks': {
            'delta': tracker.entry_greeks.delta,
            'gamma': tracker.entry_greeks.gamma,
            'theta': tracker.entry_greeks.theta,
            'vega': tracker.entry_greeks.vega,
            'iv': tracker.entry_greeks.iv,
            'underlying_price': tracker.entry_greeks.underlying_price,
            'option_price': tracker.entry_greeks.option_price,
            'dte': tracker.entry_greeks.dte
        }
    }
    
    # Verify all data is preserved
    assert tracker_dict['entry_greeks']['delta'] == 0.5
    assert tracker_dict['entry_greeks']['underlying_price'] == 450.0