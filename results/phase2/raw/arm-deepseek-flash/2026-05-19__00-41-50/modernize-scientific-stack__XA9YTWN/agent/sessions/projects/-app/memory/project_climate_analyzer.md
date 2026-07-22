---
name: project_climate_analyzer
description: "Modernized legacy Python 2.7 climate analysis code — script at /app/analyze_climate_modern.py, original at /app/climate_analyzer/analyze_climate.py"
metadata: 
  node_type: memory
  type: project
  originSessionId: 5ee8cd47-cb82-486e-9d1d-27214adeccdb
---

Modernized the legacy Python 2.7 climate analysis script (`/app/climate_analyzer/analyze_climate.py`) into a Python 3 version at `/app/analyze_climate_modern.py`. Key migrations: ConfigParser→configparser, xrange→range, print statement→function, deprecated pandas/NumPy APIs replaced, hardcoded Unicode paths fixed. Reads CSV from `/app/climate_analyzer/sample_data/climate_data.csv`, config from `/app/climate_analyzer/config.ini`. Outputs mean temperatures for stations 101 (-15.5°C) and 102 (30.3°C). Dependencies defined in `/app/pyproject.toml` (numpy>=1.24, pandas>=2.0, matplotlib>=3.7).

**Why:** Original code was Python 2.7 only, with hardcoded wrong paths and Unicode encoding issues.

**How to apply:** The modern script auto-resolves paths relative to its own location — run it from anywhere with `python /app/analyze_climate_modern.py`.
