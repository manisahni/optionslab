# File: PRPs/EXAMPLE_theta_lib_prp.md

# PRP: ThetaData Python Client Library

## Context
… (fill in summary from API docs and examples)

## Objectives
- Wrap REST and streaming endpoints
- Provide sync and async APIs
- Handle pagination, errors, retries
- Package for PyPI

## Implementation Plan
1. Define `client.py` with auth and session lifecycle.
2. Implement `rest.py` for `/v2/list/contracts` and pagination.
3. Build `stream.py` for WebSocket feeds.
4. Add sync and async interfaces.
5. Write `setup.py`/`pyproject.toml` for packaging.
6. Integrate GitHub Actions for CI and coverage.

## Testing
- `tests/test_rest.py` for pagination logic.
- `tests/test_stream.py` for mock WebSocket messages.
- Coverage threshold: 90%.

## Documentation
- Use Sphinx to generate docs under `docs/`.
- Include usage examples in `docs/usage.md`.