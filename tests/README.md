# Tests — Popular Books Tracker

This directory contains the project's tests organized into three levels.

## Structure

```
tests/
├── unit/                       # Unit tests (no AWS dependencies)
│   ├── test_scraper.py         # Tests for the most_read_scraper class
│   └── test_lambda_handler.py  # Tests for the Lambda handler
├── integration/
│   └── README.md               # Integration test scripts (AWS required)
├── configuration/
│   └── README.md               # Infrastructure validation tests
└── README.md                   # This file
```

## Test levels

| Level | What it tests | Requires AWS | Speed |
|-------|--------------|-------------|-------|
| **Unit** | Isolated business logic with mocks | No | Fast (~5 s) |
| **Integration** | Real interaction between AWS services | Yes | Slow (~15 min) |
| **Configuration** | State of deployed AWS infrastructure | Yes | Medium (~1 min) |

## Quick run (unit tests)

```bash
# From the project root
pip install pytest pytest-cov beautifulsoup4 requests

pytest tests/unit/ -v

# With coverage
pytest tests/unit/ -v --cov=src/scraper --cov-report=term-missing
```

## Expected coverage

| Module | Target coverage |
|--------|----------------|
| `src/scraper/scraper.py` | ≥ 85% |
| `src/scraper/lamda_function.py` | ≥ 80% |
