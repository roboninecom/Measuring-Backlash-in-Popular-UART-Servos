# Backlash Test Utilities

Python helpers for analyzing and plotting the CSV logs produced by the Node.js servo sweeps:
- `log_calc.py` / `log_calc_single.py` compute relaxed/stretch metrics for paired or single-motor sweeps.
- `log_viz.py` / `log_viz_single.py` create Plotly visualizations of the recorded motion.

## Environment Setup
```bash
python3 -m venv .venv
source .venv/bin/activate      # use .\.venv\Scripts\activate on Windows
pip install pandas numpy plotly
```

## Usage
- Run the analyzers with `python log_calc.py <path/to/motor_telemetry.csv>` or `python log_calc_single.py ...`.
- Launch the visualizers with `python log_viz.py <csv>` or `python log_viz_single.py <csv>`; an interactive Plotly window will open.
