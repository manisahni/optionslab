# Contributing to 0DTE Trading Analysis System

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Respect differing opinions and experiences

## How to Contribute

### Reporting Issues

1. **Check existing issues** first to avoid duplicates
2. **Use issue templates** when available
3. **Provide details**:
   - Environment (OS, Python version)
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages/logs

### Suggesting Features

1. **Open a discussion** first for major features
2. **Explain the use case** and benefits
3. **Consider implementation** complexity
4. **Be open to feedback** and alternatives

### Submitting Code

#### Setup Development Environment

```bash
# Fork and clone
git clone https://github.com/YOUR-USERNAME/odtedb.git
cd odtedb

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install in development mode
pip install -r requirements.txt
pip install -e .

# Install dev dependencies
pip install pytest black flake8 mypy
```

#### Development Workflow

1. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes**
   - Write clean, documented code
   - Add tests for new features
   - Update documentation

3. **Test your changes**
   ```bash
   # Run tests
   pytest

   # Check code style
   black --check .
   flake8 .

   # Type checking
   mypy .
   ```

4. **Commit with descriptive messages**
   ```bash
   git commit -m "feat: add new volatility indicator"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting)
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Maintenance tasks

Examples:
```
feat: add 2-minute ORB timeframe option
fix: correct P&L calculation for futures
docs: update API setup instructions
```

## Code Standards

### Python Style Guide

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use [Black](https://github.com/psf/black) for formatting
- Maximum line length: 88 characters
- Use type hints where possible

### Code Organization

```python
# Imports grouped and ordered
import os
import sys
from datetime import datetime

import pandas as pd
import numpy as np

from .utils import calculate_returns

# Constants in UPPER_CASE
DEFAULT_TIMEFRAME = 15

# Classes use CamelCase
class ORBStrategy:
    """
    Docstring describing the class.
    
    Args:
        timeframe: Opening range duration in minutes
    """
    
    def __init__(self, timeframe: int = DEFAULT_TIMEFRAME):
        self.timeframe = timeframe
    
    def calculate_range(self, df: pd.DataFrame) -> dict:
        """
        Calculate opening range.
        
        Args:
            df: DataFrame with OHLC data
            
        Returns:
            Dictionary with high, low, and range
        """
        # Implementation here
        pass
```

### Testing

- Write tests for new features
- Aim for >80% code coverage
- Use pytest for testing
- Mock external dependencies

Example test:
```python
import pytest
from dte_agent.strategies.orb import ORBStrategy

def test_orb_calculation():
    """Test ORB range calculation"""
    strategy = ORBStrategy(timeframe=15)
    df = create_test_data()
    
    result = strategy.calculate_opening_range(df)
    
    assert result['high'] == 100.5
    assert result['low'] == 99.5
    assert result['range'] == 1.0
```

### Documentation

- Add docstrings to all public functions/classes
- Update README for significant changes
- Include examples in docstrings
- Document breaking changes

## Pull Request Process

1. **Ensure all tests pass**
2. **Update documentation** if needed
3. **Add yourself to contributors** (if first contribution)
4. **Request review** from maintainers
5. **Address feedback** promptly
6. **Squash commits** if requested

### PR Checklist

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] No merge conflicts
- [ ] Includes tests for new features

## Areas for Contribution

### High Priority
- Additional trading strategies
- Performance optimizations
- Test coverage improvements
- Documentation enhancements

### Feature Ideas
- More technical indicators
- Real-time trading integration
- Advanced backtesting features
- Machine learning models
- Web API endpoints

### Good First Issues
Look for issues labeled `good first issue` for beginner-friendly tasks.

## Questions?

- Open a discussion for general questions
- Tag @manisahni for strategy-specific questions
- Join our community chat (when available)

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Given credit in documentation

Thank you for helping improve the 0DTE Trading Analysis System!