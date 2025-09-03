# Testing Templates

This directory contains reusable testing templates for systematic validation of options trading system components. These templates are based on lessons learned from comprehensive testing of the daily-optionslab system.

## Template Overview

### Phase 1: Component Testing Templates
- **`phase1_component_test_template.py`** - Test individual components in isolation
- Tests imports, basic functionality, edge cases, and performance
- Validates function signatures dynamically to catch interface changes

### Phase 2: Integration Testing Templates  
- **`phase2_integration_test_template.py`** - Test component interactions
- Validates data flow between components
- Tests error handling and end-to-end pipeline functionality
- Documents data quality insights (50% zero prices in options data is NORMAL)

### Phase 3: Strategy Testing Templates
- **`phase3_strategy_test_template.py`** - Test complete position lifecycle
- Entry, tracking, exit conditions, and P&L calculations
- Greeks evolution analysis and commission impact

## Quick Start Guide

### 1. Copy Template for Your Testing Needs
```bash
# For component testing
cp testing_templates/phase1_component_test_template.py test_my_component.py

# For integration testing  
cp testing_templates/phase2_integration_test_template.py test_my_integration.py

# For strategy testing
cp testing_templates/phase3_strategy_test_template.py test_my_strategy.py
```

### 2. Customize the Template
Edit the TODO sections in the template:
- Import your specific components
- Define your test cases
- Set appropriate thresholds
- Add component-specific validations

### 3. Run the Test
```bash
python test_my_component.py
```

The template will provide comprehensive logging and clear pass/fail results.

## Template Features

### Comprehensive Logging
- Audit trails for all operations
- Clear progress indicators
- Performance benchmarks
- Memory usage tracking

### Defensive Programming Patterns
- Guard clauses for edge cases
- Graceful error handling
- Function signature validation
- Dynamic introspection

### Data Quality Awareness
- Validates expected patterns (50% zero prices)
- Checks data correlations (zero close = zero volume)
- Documents normal vs abnormal data characteristics

### Interactive Testing Support
- Clear pass/fail criteria
- Detailed error reporting
- Performance thresholds
- Actionable next steps

## Customization Guidelines

### Component Testing Customization
1. **Import Section**: Replace with your component imports
2. **Function Validation**: Update required parameters list
3. **Test Cases**: Define appropriate test inputs and expected outputs
4. **Performance Thresholds**: Set realistic benchmarks
5. **Edge Cases**: Add component-specific edge scenarios

### Integration Testing Customization  
1. **Component Chain**: Define your specific integration flow
2. **Data Quality Checks**: Add domain-specific validations
3. **Error Scenarios**: Define realistic error conditions
4. **Pipeline Logic**: Customize end-to-end workflow

### Strategy Testing Customization
1. **Strategy Config**: Define your strategy parameters
2. **Entry Logic**: Customize option selection criteria
3. **Exit Rules**: Define profit/loss/time/Greeks exits
4. **P&L Calculations**: Add strategy-specific cost components

## Best Practices

### Template Usage
- Always copy templates, never modify originals
- Use descriptive names for your test files
- Document any deviations from template patterns
- Maintain test files alongside production code

### Test Development
- Start with simplest template (Phase 1)
- Progress through phases systematically
- Get user approval before moving to next phase
- Document discovered edge cases

### Error Handling
- Use guard clauses for invalid inputs
- Return safe defaults (0, None) rather than crashing
- Log all error conditions with context
- Test error scenarios explicitly

## Template Evolution

These templates are living documents that should evolve based on:
- New edge cases discovered
- Performance optimization insights
- Additional validation requirements
- Integration pattern changes

### Contributing Improvements
When you discover new testing patterns or edge cases:
1. Document the finding
2. Update relevant template with the improvement
3. Add notes about why the change was needed
4. Update this README with new best practices

## Common Testing Patterns

### Data Quality Validation Pattern
```python
# Always check for expected options data patterns
zero_close = (data['close'] == 0).sum()
zero_volume = (data['volume'] == 0).sum()
print(f"Zero close prices: {zero_close:,} ({zero_close/len(data):.1%})")
assert zero_close == zero_volume, "Close=0 should equal volume=0"
```

### Guard Clause Pattern
```python
def robust_function(data, price):
    # Always validate inputs first
    if data is None or len(data) == 0:
        print("⚠️ AUDIT: No data provided")
        return None, "No data"
    
    if price <= 0:
        print("⚠️ AUDIT: Invalid price")
        return 0, 0
    
    # Main logic here
    return result
```

### Performance Benchmarking Pattern
```python
import time
start_time = time.time()
result = function_under_test(large_dataset)
duration = time.time() - start_time

records_per_sec = len(result) / duration if duration > 0 else 0
if records_per_sec > THRESHOLD:
    print("✅ Performance acceptable")
else:
    print("⚠️ Performance below threshold")
```

## Integration with Main System

These templates are designed to work with the daily-optionslab system structure:
- Import paths assume standard `optionslab/` module structure
- Data paths point to standard SPY options dataset
- Configuration formats match YAML strategy definitions

For other systems, update:
- Import statements
- Data file paths  
- Configuration formats
- Performance thresholds

## Troubleshooting

### Common Issues
1. **Import Errors**: Check that your system path includes the project root
2. **Data File Not Found**: Update DATA_FILE path for your system
3. **Performance Thresholds**: Adjust based on your hardware capabilities
4. **Test Failures**: Review TODO sections for incomplete customization

### Getting Help
1. Check the main CLAUDE.md for testing methodology
2. Review TESTING_METHODOLOGY.md for detailed procedures
3. Examine existing test files (test_phase*.py) for examples
4. Run templates with minimal changes first, then customize

Remember: **The goal of testing is not to prove code works, but to discover where it doesn't work so you can fix it before it matters.**