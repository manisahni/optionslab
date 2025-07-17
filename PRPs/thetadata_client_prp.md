# PRP: ThetaData Python Client Library

## Context

Based on the requirements from `INITIAL.md`:
- **Feature**: Python client for ThetaData covering REST & streaming, sync & async, tests, docs, packaging
- **Examples Available**: `rest_request.py`, `streaming_example.py`, `pagination_util.py`
- **Documentation**: Local summary at `docs/ThetaData_API_Summary.txt` and official docs at https://http-docs.thetadata.us/
- **Key Considerations**: Rate limits, port configuration, PyPI packaging

### Key Patterns from Examples:
1. **REST Requests** (`rest_request.py`):
   - Base URL: `https://api.thetadata.us/v2/`
   - Endpoint example: `/list/contracts` with params `root` and `exp`
   - Error handling via `raise_for_status()`
   - JSON response parsing

2. **WebSocket Streaming** (`streaming_example.py`):
   - WebSocket URL: `ws://localhost:25510/stream/quotes`
   - Async WebSocket connections using `websockets`
   - Subscription format: `SUBSCRIBE {'root':'SYMBOL'}`
   - Continuous message reception loop

3. **Pagination** (`pagination_util.py`):
   - Generator pattern for iterating through paginated results
   - Response contains `results` array and optional `nextUrl`
   - Yields items from each page

### API Summary from Documentation:
- **REST Endpoints**:
  - `/v2/list/contracts`: List option chains
  - `/v2/history/options`: Fetch historical IV data
  - Additional endpoints per official documentation
  
- **Streaming Endpoints**:
  - `/stream/quotes`: Real-time quotes
  - `/stream/trades`: Real-time trades
  - Additional streaming channels available

## Objectives

1. **Core Python Client Implementation**
   - Unified client supporting both sync and async interfaces
   - Modular design: `client.py`, `rest.py`, `stream.py`, `models.py`
   - Comprehensive error handling and retry logic

2. **REST API Support**
   - Full coverage of ThetaData REST endpoints
   - Automatic pagination using patterns from `pagination_util.py`
   - Rate limiting compliance
   - Connection pooling for performance

3. **WebSocket Streaming Support**
   - Real-time quotes and trades streaming
   - Auto-reconnection on disconnect
   - Port configuration support (default: 25510)
   - Message buffering and error recovery

4. **Production-Ready Package**
   - Pydantic data models with validation
   - Full test suite with pytest
   - Type hints throughout (mypy compliant)
   - Sphinx documentation with examples
   - PyPI-ready packaging configuration

## Implementation Plan

### Phase 1: Project Setup and Core Structure

1. **Initialize Project Structure**
   ```bash
   mkdir -p thetadata/{tests,docs}
   touch thetadata/{__init__.py,client.py,rest.py,stream.py,models.py,exceptions.py,utils.py}
   touch tests/{__init__.py,test_client.py,test_rest.py,test_stream.py,test_models.py}
   touch {setup.py,pyproject.toml,requirements.txt,requirements-dev.txt}
   ```

2. **Setup Development Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -e ".[dev]"
   ```

3. **Configure pyproject.toml**
   ```toml
   [build-system]
   requires = ["setuptools>=61.0", "wheel"]
   build-backend = "setuptools.build_meta"

   [project]
   name = "thetadata"
   version = "0.1.0"
   description = "Python client for ThetaData API"
   requires-python = ">=3.8"
   dependencies = [
       "requests>=2.28.0",
       "websockets>=10.0",
       "pydantic>=2.0",
       "httpx>=0.24.0",
       "tenacity>=8.0.0",
   ]

   [project.optional-dependencies]
   dev = [
       "pytest>=7.0",
       "pytest-asyncio>=0.21.0",
       "pytest-cov>=4.0",
       "mypy>=1.0",
       "black>=23.0",
       "ruff>=0.1.0",
       "sphinx>=6.0",
   ]
   ```

### Phase 2: Core Components Implementation

1. **Implement Base Exceptions** (`exceptions.py`)
   ```python
   class ThetaDataError(Exception):
       """Base exception for ThetaData client"""
       pass

   class AuthenticationError(ThetaDataError):
       """Raised when API authentication fails"""
       pass

   class RateLimitError(ThetaDataError):
       """Raised when rate limit is exceeded"""
       pass

   class ConnectionError(ThetaDataError):
       """Raised when connection fails"""
       pass
   ```

   **Validation**: `python -m pytest tests/test_exceptions.py`

2. **Implement Utility Functions** (`utils.py`)
   ```python
   from typing import Dict, Any
   from tenacity import retry, stop_after_attempt, wait_exponential

   @retry(
       stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=4, max=10)
   )
   async def retry_async(func, *args, **kwargs):
       """Retry async function with exponential backoff"""
       return await func(*args, **kwargs)

   def build_headers(api_key: str) -> Dict[str, str]:
       """Build request headers with authentication"""
       return {
           "Authorization": f"Bearer {api_key}",
           "Content-Type": "application/json",
       }
   ```

   **Validation**: `python -m pytest tests/test_utils.py`

3. **Implement Data Models** (`models.py`)
   ```python
   from pydantic import BaseModel, Field
   from datetime import datetime
   from typing import Optional, List

   class Contract(BaseModel):
       root: str
       expiration: datetime
       strike: float
       right: str = Field(..., regex="^(CALL|PUT)$")
       
   class Quote(BaseModel):
       symbol: str
       bid: float
       ask: float
       timestamp: datetime
       
   class PaginatedResponse(BaseModel):
       results: List[Any]
       next_url: Optional[str] = Field(None, alias="nextUrl")
   ```

   **Validation**: `python -m mypy thetadata/models.py`

### Phase 3: REST Client Implementation

1. **Implement Rate Limiter** (`utils.py` addition)
   ```python
   import time
   from collections import deque
   import asyncio
   
   class RateLimiter:
       """Token bucket rate limiter for API calls"""
       def __init__(self, calls_per_second: int = 10):
           self.calls_per_second = calls_per_second
           self.min_interval = 1.0 / calls_per_second
           self.last_call = 0.0
           
       async def acquire(self):
           """Wait if necessary to respect rate limit"""
           current = time.time()
           time_since_last = current - self.last_call
           if time_since_last < self.min_interval:
               await asyncio.sleep(self.min_interval - time_since_last)
           self.last_call = time.time()
   ```

2. **Implement REST Client** (`rest.py`)
   ```python
   import httpx
   from typing import Optional, Dict, Any, AsyncIterator
   from .models import PaginatedResponse
   from .utils import retry_async, build_headers, RateLimiter
   from .exceptions import AuthenticationError, RateLimitError

   class RESTClient:
       def __init__(self, api_key: str, base_url: str = "https://api.thetadata.us/v2", 
                    rate_limit: int = 10):
           self.api_key = api_key
           self.base_url = base_url
           self.rate_limiter = RateLimiter(rate_limit)
           self.session = httpx.Client(headers=build_headers(api_key))
           
       async def list_contracts(self, root: str, exp: str) -> Dict[str, Any]:
           """List option contracts for a given root and expiration"""
           await self.rate_limiter.acquire()
           response = await retry_async(
               self.session.get,
               f"{self.base_url}/list/contracts",
               params={"root": root, "exp": exp}
           )
           self._handle_response(response)
           return response.json()
           
       async def paginate(self, endpoint: str, params: Dict[str, Any]) -> AsyncIterator[Any]:
           """Handle paginated responses"""
           next_url = f"{self.base_url}/{endpoint}"
           while next_url:
               response = await retry_async(
                   self.session.get,
                   next_url,
                   params=params if next_url.startswith(self.base_url) else None
               )
               self._handle_response(response)
               data = PaginatedResponse(**response.json())
               for item in data.results:
                   yield item
               next_url = data.next_url
               
       def _handle_response(self, response: httpx.Response):
           """Handle API response errors"""
           if response.status_code == 401:
               raise AuthenticationError("Invalid API key")
           elif response.status_code == 429:
               raise RateLimitError("Rate limit exceeded")
           response.raise_for_status()
   ```

   **Validation**: 
   ```bash
   python -m pytest tests/test_rest.py -v
   python -m mypy thetadata/rest.py
   ```

### Phase 4: WebSocket Client Implementation

1. **Implement WebSocket Client** (`stream.py`)
   ```python
   import asyncio
   import json
   from typing import Dict, Any, Callable, Optional
   import websockets
   from websockets.exceptions import ConnectionClosed
   from .exceptions import ConnectionError
   
   class StreamClient:
       def __init__(self, host: str = "localhost", port: int = 25510):
           self.host = host
           self.port = port
           self.url = f"ws://{host}:{port}/stream"
           self.ws: Optional[websockets.WebSocketClientProtocol] = None
           self.subscriptions: Dict[str, Callable] = {}
           self.reconnect_delay = 5
           
       async def connect(self):
           """Establish WebSocket connection"""
           try:
               self.ws = await websockets.connect(self.url)
           except Exception as e:
               raise ConnectionError(f"Failed to connect: {e}")
               
       async def subscribe(self, symbol: str, callback: Callable):
           """Subscribe to symbol updates"""
           if not self.ws:
               await self.connect()
               
           self.subscriptions[symbol] = callback
           message = json.dumps({"action": "SUBSCRIBE", "root": symbol})
           await self.ws.send(message)
           
       async def listen(self):
           """Listen for messages with auto-reconnection"""
           while True:
               try:
                   if not self.ws:
                       await self.connect()
                       # Re-subscribe to all symbols
                       for symbol in self.subscriptions:
                           message = json.dumps({"action": "SUBSCRIBE", "root": symbol})
                           await self.ws.send(message)
                           
                   async for message in self.ws:
                       data = json.loads(message)
                       symbol = data.get("root")
                       if symbol and symbol in self.subscriptions:
                           await self.subscriptions[symbol](data)
                           
               except ConnectionClosed:
                   self.ws = None
                   await asyncio.sleep(self.reconnect_delay)
               except Exception as e:
                   print(f"Stream error: {e}")
                   await asyncio.sleep(self.reconnect_delay)
   ```

   **Validation**: `python -m pytest tests/test_stream.py -v`

### Phase 5: Main Client Implementation

1. **Implement Main Client** (`client.py`)
   ```python
   from typing import Optional, Dict, Any, AsyncIterator
   import asyncio
   from .rest import RESTClient
   from .stream import StreamClient
   
   class ThetaDataClient:
       """Main client for ThetaData API"""
       
       def __init__(self, api_key: str):
           self.api_key = api_key
           self.rest = RESTClient(api_key)
           self.stream = StreamClient()
           
       # Sync methods
       def list_contracts(self, root: str, exp: str) -> Dict[str, Any]:
           """Synchronously list option contracts"""
           return asyncio.run(self.rest.list_contracts(root, exp))
           
       def iterate_history(self, endpoint: str, params: Dict[str, Any]):
           """Synchronously iterate through paginated historical data"""
           async def _iterate():
               results = []
               async for item in self.rest.paginate(endpoint, params):
                   results.append(item)
               return results
           return asyncio.run(_iterate())
           
       # Async methods
       async def list_contracts_async(self, root: str, exp: str) -> Dict[str, Any]:
           """Asynchronously list option contracts"""
           return await self.rest.list_contracts(root, exp)
           
       async def stream_quotes(self, symbol: str, callback):
           """Stream real-time quotes for a symbol"""
           await self.stream.subscribe(symbol, callback)
           
       async def start_streaming(self):
           """Start the streaming connection"""
           await self.stream.listen()
   ```

   **Validation**: `python -m pytest tests/test_client.py -v`

### Phase 6: Testing Strategy

1. **Create Test Fixtures** (`tests/conftest.py`)
   ```python
   import pytest
   from unittest.mock import Mock, AsyncMock
   import httpx
   
   @pytest.fixture
   def mock_httpx_client(monkeypatch):
       """Mock httpx client for testing"""
       mock_client = Mock(spec=httpx.Client)
       mock_response = Mock()
       mock_response.status_code = 200
       mock_response.json.return_value = {
           "results": [{"symbol": "AAPL"}],
           "nextUrl": None
       }
       mock_client.get.return_value = mock_response
       return mock_client
       
   @pytest.fixture
   def api_key():
       return "test_api_key"
   ```

2. **Unit Tests Example** (`tests/test_rest.py`)
   ```python
   import pytest
   from thetadata.rest import RESTClient
   from thetadata.exceptions import AuthenticationError
   
   @pytest.mark.asyncio
   async def test_list_contracts(api_key, mock_httpx_client):
       client = RESTClient(api_key)
       client.session = mock_httpx_client
       
       result = await client.list_contracts("AAPL", "20260116")
       assert result["results"][0]["symbol"] == "AAPL"
       
   @pytest.mark.asyncio
   async def test_authentication_error(api_key, mock_httpx_client):
       mock_httpx_client.get.return_value.status_code = 401
       client = RESTClient(api_key)
       client.session = mock_httpx_client
       
       with pytest.raises(AuthenticationError):
           await client.list_contracts("AAPL", "20260116")
   ```

3. **Integration Tests** (`tests/test_integration.py`)
   ```python
   import pytest
   from thetadata import ThetaDataClient
   
   @pytest.mark.integration
   def test_end_to_end_flow():
       # Requires valid API key
       client = ThetaDataClient(api_key="YOUR_API_KEY")
       contracts = client.list_contracts("SPY", "20260116")
       assert len(contracts["results"]) > 0
   ```

   **Validation**: 
   ```bash
   python -m pytest tests/ -v --cov=thetadata --cov-report=html
   python -m pytest tests/ -m "not integration"  # Skip integration tests
   ```

### Phase 7: Documentation

1. **Create Sphinx Documentation** (`docs/conf.py`)
   ```python
   project = 'ThetaData Python Client'
   author = 'Your Name'
   extensions = [
       'sphinx.ext.autodoc',
       'sphinx.ext.napoleon',
       'sphinx.ext.viewcode',
   ]
   html_theme = 'sphinx_rtd_theme'
   ```

2. **Usage Examples** (`docs/examples.rst`)
   ```rst
   Usage Examples
   ==============
   
   Basic Usage
   -----------
   
   .. code-block:: python
   
       from thetadata import ThetaDataClient
       
       # Initialize client
       client = ThetaDataClient(api_key="YOUR_API_KEY")
       
       # List option contracts
       contracts = client.list_contracts("AAPL", "20260116")
       
       # Stream real-time data
       async def handle_quote(data):
           print(f"Quote: {data}")
           
       async def main():
           await client.stream_quotes("SPY", handle_quote)
           await client.start_streaming()
   ```

   **Validation**: 
   ```bash
   cd docs && make html
   open _build/html/index.html
   ```

### Phase 8: CI/CD Pipeline

1. **GitHub Actions Workflow** (`.github/workflows/ci.yml`)
   ```yaml
   name: CI
   
   on: [push, pull_request]
   
   jobs:
     test:
       runs-on: ubuntu-latest
       strategy:
         matrix:
           python-version: ["3.8", "3.9", "3.10", "3.11"]
           
       steps:
       - uses: actions/checkout@v3
       - name: Set up Python
         uses: actions/setup-python@v4
         with:
           python-version: ${{ matrix.python-version }}
           
       - name: Install dependencies
         run: |
           pip install -e ".[dev]"
           
       - name: Run tests
         run: |
           python -m pytest tests/ -v --cov=thetadata
           
       - name: Type checking
         run: |
           python -m mypy thetadata/
           
       - name: Linting
         run: |
           python -m ruff check thetadata/
           python -m black --check thetadata/
   ```

## Testing

### Test Structure
```
tests/
├── conftest.py          # Shared fixtures
├── test_client.py       # Client tests
├── test_rest.py         # REST API tests
├── test_stream.py       # WebSocket tests
├── test_models.py       # Data model tests
├── test_utils.py        # Utility tests
└── test_integration.py  # End-to-end tests
```

### Key Testing Patterns

1. **Mock External Dependencies**
   ```python
   @pytest.fixture
   def mock_websocket(monkeypatch):
       mock_ws = AsyncMock()
       mock_ws.send = AsyncMock()
       mock_ws.__aiter__.return_value = iter([
           '{"root": "SPY", "bid": 450.00, "ask": 450.05}'
       ])
       monkeypatch.setattr("websockets.connect", AsyncMock(return_value=mock_ws))
       return mock_ws
   ```

2. **Test Retry Logic**
   ```python
   @pytest.mark.asyncio
   async def test_retry_on_failure(mock_httpx_client):
       mock_httpx_client.get.side_effect = [
           httpx.TimeoutException("Timeout"),
           Mock(status_code=200, json=lambda: {"results": []})
       ]
       client = RESTClient("api_key")
       result = await client.list_contracts("AAPL", "20260116")
       assert mock_httpx_client.get.call_count == 2
   ```

3. **Test Pagination**
   ```python
   @pytest.mark.asyncio
   async def test_pagination():
       responses = [
           {"results": [1, 2], "nextUrl": "http://api/page2"},
           {"results": [3, 4], "nextUrl": None}
       ]
       # Test full pagination flow
   ```

## Documentation

### Documentation Structure
```
docs/
├── index.rst           # Main documentation page
├── quickstart.rst      # Getting started guide
├── api.rst            # API reference
├── examples.rst       # Usage examples
└── changelog.rst      # Version history
```

### Key Documentation Elements

1. **API Reference with Type Hints**
   ```python
   def list_contracts(self, root: str, exp: str) -> Dict[str, Any]:
       """
       List option contracts for a given underlying and expiration.
       
       Args:
           root: The underlying symbol (e.g., "AAPL")
           exp: Expiration date in YYYYMMDD format
           
       Returns:
           Dictionary containing contract details
           
       Raises:
           AuthenticationError: If API key is invalid
           RateLimitError: If rate limit is exceeded
           
       Example:
           >>> client.list_contracts("AAPL", "20260116")
           {"results": [{"strike": 150.0, "right": "CALL", ...}]}
       """
   ```

2. **Comprehensive Examples**
   - Basic synchronous usage
   - Asynchronous usage
   - Streaming data handling
   - Error handling patterns
   - Pagination examples
   - Rate limiting strategies

## Error Handling Patterns

### Retry Strategy
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))
)
async def make_request(self, *args, **kwargs):
    """Make HTTP request with retry logic"""
    pass
```

### Rate Limiting
```python
class RateLimiter:
    def __init__(self, calls: int, period: float):
        self.calls = calls
        self.period = period
        self.timestamps = deque()
        
    async def acquire(self):
        now = time.time()
        # Remove old timestamps
        while self.timestamps and self.timestamps[0] < now - self.period:
            self.timestamps.popleft()
            
        if len(self.timestamps) >= self.calls:
            sleep_time = self.period - (now - self.timestamps[0])
            await asyncio.sleep(sleep_time)
            
        self.timestamps.append(now)
```

### Connection Recovery
```python
async def maintain_connection(self):
    """Maintain WebSocket connection with automatic recovery"""
    while self.running:
        try:
            await self.connect()
            await self.listen()
        except ConnectionClosed:
            logger.warning("Connection lost, reconnecting...")
            await asyncio.sleep(self.reconnect_delay)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await asyncio.sleep(self.reconnect_delay * 2)
```

## Validation Commands

### Development Workflow
```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests with coverage
python -m pytest tests/ -v --cov=thetadata --cov-report=term-missing

# Type checking
python -m mypy thetadata/ --strict

# Linting
python -m ruff check thetadata/
python -m black thetadata/ tests/

# Build documentation
cd docs && make clean html

# Build distribution
python -m build

# Test installation
pip install dist/thetadata-0.1.0-py3-none-any.whl
```

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.0.261
    hooks:
      - id: ruff
        
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.2.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

## PyPI Packaging

### Package Configuration (`setup.py`)
```python
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="thetadata",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Python client for ThetaData API - REST and streaming market data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/thetadata-python",
    packages=find_packages(exclude=["tests*", "docs*", "examples*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Typing :: Typed",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
        "httpx>=0.24.0",
        "websockets>=10.0",
        "pydantic>=2.0",
        "tenacity>=8.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0",
            "mypy>=1.0",
            "black>=23.0",
            "ruff>=0.1.0",
            "sphinx>=6.0",
            "twine>=4.0",
        ]
    },
)
```

### Publishing Process
```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build distribution
python -m build

# Test with TestPyPI first
python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ thetadata

# Upload to PyPI
python -m twine upload dist/*
```

## Success Criteria

1. **Code Quality**
   - [ ] 90%+ test coverage
   - [ ] Zero mypy errors with strict mode
   - [ ] All linting checks pass
   - [ ] Documentation builds without warnings

2. **Functionality**
   - [ ] All REST endpoints implemented per API docs
   - [ ] WebSocket streaming (quotes/trades) works reliably
   - [ ] Automatic retry and reconnection logic
   - [ ] Rate limiting compliance (configurable)
   - [ ] Port configuration support

3. **Developer Experience**
   - [ ] Clear, comprehensive documentation
   - [ ] Intuitive API design (sync and async)
   - [ ] Helpful error messages
   - [ ] Rich type hints throughout

4. **Production Readiness**
   - [ ] Passes all CI/CD checks
   - [ ] Published to PyPI as 'thetadata'
   - [ ] Performance benchmarks documented
   - [ ] Examples match those in `examples/` directory