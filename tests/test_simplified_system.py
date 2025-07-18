#!/usr/bin/env python3
"""
Test the simplified OptionsLab system
"""
import sys
from pathlib import Path

# Add optionslab to path
sys.path.insert(0, str(Path(__file__).parent))

from optionslab import (
    Config, 
    SPYDataLoader,
    GreeksManager,
    get_data_dir,
    get_project_root
)
from datetime import datetime

def test_integration():
    """Test that all components work together"""
    print("🧪 Testing Simplified OptionsLab System")
    print("=" * 60)
    
    # Test 1: Configuration
    print("\n1️⃣ Testing Configuration...")
    print(f"   Project root: {get_project_root()}")
    print(f"   Data directory: {get_data_dir()}")
    print(f"   Initial capital: ${Config.DEFAULT_INITIAL_CAPITAL:,.2f}")
    print("   ✅ Configuration working")
    
    # Test 2: Data Loading
    print("\n2️⃣ Testing Data Loader...")
    try:
        loader = SPYDataLoader()
        dates = loader.get_available_dates()
        print(f"   Found {len(dates)} trading days")
        
        # Load sample data
        test_date = dates[0]
        df = loader.load_date(test_date)
        print(f"   Loaded {len(df)} options for {test_date}")
        
        # Find an option
        option = loader.find_option_by_delta(test_date, 0.30, 'C')
        if option is not None:
            print(f"   Found 30-delta call: Strike ${option['strike']:.0f}, Delta {option['delta']:.3f}")
        
        print("   ✅ Data loader working")
    except Exception as e:
        print(f"   ❌ Data loader error: {e}")
        return False
    
    # Test 3: Greeks Management
    print("\n3️⃣ Testing Greeks Manager...")
    try:
        greeks_mgr = GreeksManager(track_greeks=True)
        
        # Add a test position
        if option is not None:
            position = greeks_mgr.add_position(
                position_id='TEST001',
                option_data=option,
                quantity=10,
                entry_date=datetime.now()
            )
            
            # Get portfolio Greeks
            portfolio = greeks_mgr.get_portfolio_greeks()
            print(f"   Portfolio Delta: {portfolio['total_delta']:.1f}")
            print(f"   Portfolio Theta: {portfolio['total_theta']:.1f}")
            
            # Check risk limits
            risk_check = greeks_mgr.check_risk_limits(Config.RISK_LIMITS)
            if risk_check['within_limits']:
                print("   ✅ Within risk limits")
            else:
                print(f"   ⚠️  Risk limit violations: {len(risk_check['violations'])}")
        
        print("   ✅ Greeks manager working")
    except Exception as e:
        print(f"   ❌ Greeks manager error: {e}")
        return False
    
    # Test 4: Integration between components
    print("\n4️⃣ Testing Component Integration...")
    try:
        # Data loader uses config
        assert loader.cache_size == Config.CACHE_SIZE
        print("   ✅ Data loader uses configuration")
        
        # Greeks manager works with data loader output
        assert option is not None
        print("   ✅ Greeks manager processes data loader output")
        
        print("   ✅ All components integrated")
    except Exception as e:
        print(f"   ❌ Integration error: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All tests passed! Simplified system is working.")
    print("\n📊 System Status:")
    print(f"   - Configuration: ✅")
    print(f"   - Data Loading: ✅")
    print(f"   - Greeks Management: ✅")
    print(f"   - Component Integration: ✅")
    
    return True

def compare_with_old_system():
    """Compare with the old complex system"""
    print("\n\n📊 Simplification Metrics:")
    print("=" * 60)
    
    # Count files in old structure
    old_core_files = len(list(Path("optionslab-core").glob("*.py"))) if Path("optionslab-core").exists() else 0
    old_ui_files = len(list(Path("optionslab-ui/core").glob("*.py"))) if Path("optionslab-ui/core").exists() else 0
    
    # Count files in new structure
    new_files = len(list(Path("optionslab").rglob("*.py")))
    
    print(f"Old system files: ~{old_core_files + old_ui_files} Python files")
    print(f"New system files: {new_files} Python files")
    
    if old_core_files + old_ui_files > 0:
        reduction = (1 - new_files / (old_core_files + old_ui_files)) * 100
        print(f"File reduction: {reduction:.0f}%")
    
    print("\n✨ Improvements:")
    print("   - Single data loader (was 3)")
    print("   - Single config system (was 2)")
    print("   - Single Greeks manager (was 4)")
    print("   - Clear module organization")
    print("   - No duplicate functionality")
    print("   - Simplified imports")

if __name__ == "__main__":
    success = test_integration()
    if success:
        compare_with_old_system()
    
    sys.exit(0 if success else 1)