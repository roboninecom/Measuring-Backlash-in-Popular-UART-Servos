#!/usr/bin/env python3
import os
import sys
from typing import Dict, List

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from config_utils import (
    AnalysisConfig,
    build_phase_mask,
    build_relaxed_mask,
    build_stretch_mask,
    ensure_columns,
    find_segments,
    load_config,
    pos_col,
    target_col,
)

SHOW_OUTLINES = True


def invert(series: pd.Series, home: float) -> pd.Series:
    """Mirror position value around home (e.g., 2247 ↔ 1847)."""
    return 2 * home - series


def add_interval_shapes(fig: go.Figure, df: pd.DataFrame, mask: pd.Series, color: str, y0: float, y1: float) -> None:
    """Add rectangular outlines for contiguous mask intervals."""
    segments = find_segments(mask)
    for start_idx, end_idx in segments:
        fig.add_shape(
            type="rect",
            x0=df["t_sec"].iloc[start_idx],
            x1=df["t_sec"].iloc[end_idx],
            y0=y0,
            y1=y1,
            fillcolor=color,
            opacity=0.15,
            line=dict(color=color, width=1),
            layer="below",
        )


def build_required_columns(config: AnalysisConfig) -> List[str]:
    cols = set()
    for motor_id in config.home_motor_ids:
        cols.add(target_col(motor_id))
        cols.add(pos_col(motor_id))
    for motor_id in config.report_motor_ids:
        cols.add(target_col(motor_id))
        cols.add(pos_col(motor_id))
    for motor in config.actuated_motors:
        cols.add(target_col(motor.motor_id))
        cols.add(pos_col(motor.motor_id))
    return sorted(cols)


def compute_outline_bounds(df: pd.DataFrame, config: AnalysisConfig) -> Dict[str, float]:
    columns = [pos_col(mid) for mid in config.report_motor_ids] + [target_col(mid) for mid in config.report_motor_ids]
    columns = [col for col in columns if col in df.columns]
    if not columns:
        return {"y_min": 0.0, "y_max": 1.0}
    y_min = df[columns].min().min()
    y_max = df[columns].max().max()
    if not np.isfinite(y_min) or not np.isfinite(y_max):
        y_min, y_max = 0.0, 1.0
    if y_min == y_max:
        y_min -= 1
        y_max += 1
    padding = 0.05 * (y_max - y_min)
    return {"y_min": y_min - padding, "y_max": y_max + padding}


def add_motor_traces(fig: go.Figure, df: pd.DataFrame, config: AnalysisConfig) -> None:
    mirror_second_motor = len(config.report_motor_ids) == 2
    mirrored_id = config.report_motor_ids[1] if mirror_second_motor else None

    for idx, motor_id in enumerate(config.report_motor_ids):
        motor_name = f"Motor {motor_id}"
        target = df[target_col(motor_id)]
        position = df[pos_col(motor_id)]
        mirrored = mirrored_id is not None and motor_id == mirrored_id
        if mirrored:
            target = invert(target, config.home_position)
            position = invert(position, config.home_position)
            motor_name += " (mirrored)"

        fig.add_trace(go.Scatter(
            x=df["t_sec"],
            y=target,
            mode="lines",
            name=f"{motor_name} Target",
            line=dict(dash="dash"),
        ))

        fig.add_trace(go.Scatter(
            x=df["t_sec"],
            y=position,
            mode="lines",
            name=f"{motor_name} Position",
            line=dict(dash="solid"),
        ))


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python log_viz.py <config.json> <path_to_csv>")
        sys.exit(1)

    config_path, csv_path = sys.argv[1], sys.argv[2]

    try:
        config = load_config(config_path)
    except (OSError, ValueError) as exc:
        print(f"Error loading config: {exc}")
        sys.exit(1)

    if not os.path.exists(csv_path):
        print(f"Error: Path does not exist: {csv_path}")
        sys.exit(1)
    if not os.path.isfile(csv_path):
        print(f"Error: Not a file: {csv_path}")
        sys.exit(1)

    df = pd.read_csv(csv_path)

    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    except Exception:
        pass

    if "timestamp" in df.columns and pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["t_sec"] = (df["timestamp"] - df["timestamp"].iloc[0]).dt.total_seconds()
    else:
        df["t_sec"] = np.arange(len(df), dtype=float)

    try:
        ensure_columns(df, build_required_columns(config))
    except KeyError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    outline_bounds = compute_outline_bounds(df, config)
    phase_mask = build_phase_mask(df, config)
    relaxed_mask = build_relaxed_mask(df, config.actuated_motors) & phase_mask
    stretched_mask = pd.Series(False, index=df.index, dtype=bool)
    for motor in config.actuated_motors:
        stretched_mask |= build_stretch_mask(df, motor)

    fig = go.Figure()
    add_motor_traces(fig, df, config)

    if SHOW_OUTLINES:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color="green", width=3), name="Relaxed Region"))
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color="red", width=3), name="Stretched Region"))
        add_interval_shapes(fig, df, relaxed_mask, "green", outline_bounds["y_min"], outline_bounds["y_max"])
        add_interval_shapes(fig, df, stretched_mask, "red", outline_bounds["y_min"], outline_bounds["y_max"])

    fig.update_layout(
        title="Motor targets vs positions",
        xaxis_title="Time (seconds)",
        yaxis_title="Position",
        hovermode="x unified",
        legend_title_text="Series",
        plot_bgcolor="#ffffff",
    )

    fig.update_xaxes(showgrid=True, gridcolor="gray", gridwidth=1, griddash="dot")
    fig.update_yaxes(showgrid=True, gridcolor="gray", gridwidth=1, griddash="dot")
    fig.show()


if __name__ == "__main__":
    main()
