# BolsaStreamlit - Agent Guidelines

This is a Streamlit application for visualizing financial candlestick data with support/resistance analysis and comparison features.

## Project Overview

- **Main Application**: Streamlit web app for financial data visualization
- **Language**: Python 3.12+
- **Package Manager**: pip with pyproject.toml
- **Primary Libraries**: streamlit, plotly, pandas, yfinance, scipy

## Build/Development Commands

### Running the Application
```bash
streamlit run app.py
```

### Installing Dependencies
```bash
pip install -e .
# or
pip install pandas plotly scipy streamlit yfinance
```

### Testing
No formal test framework is currently configured. To add testing:
1. Create a `tests/` directory
2. Use `pytest` (recommended) or `unittest`
3. Add test configuration to pyproject.toml

For running individual tests (once pytest is configured):
```bash
pytest tests/test_specific_file.py -v
```

## Code Style Guidelines

### Import Organization
- Standard library imports first (pathlib, etc.)
- Third-party imports second (pandas, plotly, streamlit, scipy, yfinance)
- Local imports last (from data_utils import...)
- Use relative imports for local modules

```python
# Standard library
from pathlib import Path

# Third-party
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy.signal import argrelextrema

# Local
from data_utils import DATA_DIRS, filter_by_date
```

### Type Hints
- Use type hints for function parameters and return values
- Use modern type hint syntax (list[Path] instead of List[Path])
- File paths use pathlib.Path

```python
def load_prices(path: Path) -> tuple[pd.DataFrame, str]:
    ...
```

### Naming Conventions
- **Variables**: snake_case (filtered_data, date_column)
- **Functions**: snake_case (filter_by_date, load_prices)
- **Constants**: UPPER_SNAKE_CASE (DATA_DIRS, DEFAULT_THRESHOLD)
- **Files**: snake_case.py (data_utils.py, graficos_unicos.py)
- **Classes**: PascalCase (if using classes)

### Error Handling
- Use specific exceptions where possible
- Display user-friendly errors in Streamlit with st.error()
- Include descriptive error messages in Spanish for user-facing UI

```python
try:
    df, date_col = load_prices(path)
except Exception as exc:
    st.error(str(exc))
    return
```

### Documentation
- Use docstrings for functions explaining purpose and parameters
- Comments in Spanish for user-facing text
- Keep docstrings concise but informative

```python
def detect_support_resistance_pivots(high_prices, low_prices, order=5):
    """
    Detecta pivots (máximos y mínimos locales) para identificar soportes y resistencias.
    """
```

### Streamlit Best Practices
- Use st.cache_data() for expensive computations and data loading
- Include meaningful keys for all interactive elements
- Use st.sidebar for controls when appropriate
- Provide user feedback with st.info(), st.warning(), st.error()

```python
@st.cache_data(show_spinner=False)
def cached_load_prices(path: Path):
    return load_prices(path)
```

### Data Processing
- Use pandas for all data manipulation
- Handle timezone-aware datetime data properly
- Always validate data existence and format before processing
- Use ffill() for forward-filling missing price data

### File Organization
- `app.py` - Main Streamlit application entry point
- `data_utils.py` - Shared data loading and processing utilities
- `graficos_unicos.py` - Single chart visualization component
- `graficos_comparacion.py` - Comparison chart component
- `uso_api.py` - Data fetching utilities (yfinance API)

### Performance Considerations
- Cache expensive operations with @st.cache_data()
- Use efficient pandas operations (vectorized where possible)
- Limit data displayed in UI to reasonable amounts
- Consider data pagination for large datasets

### UI/UX Guidelines
- Use Spanish for all user-facing text
- Provide clear labels and helpful tooltips
- Use expandable sections (st.expander) for optional details
- Ensure responsive layouts with appropriate column usage
- Set chart heights appropriately (600-650px typical)

## Dependencies

Core dependencies are defined in pyproject.toml:
- streamlit>=1.52.1
- plotly>=6.5.0 
- pandas>=2.3.3
- scipy>=1.16.3
- yfinance>=1.0

When adding new dependencies, update pyproject.toml and ensure version compatibility.