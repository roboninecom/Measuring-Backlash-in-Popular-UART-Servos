#!/usr/bin/env python3
import sys
import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go

HOME = 2047

M3_RELAXED = 1747
M4_RELAXED = 2347
M3_STRETCHED = 2247
M4_STRETCHED = 1847

OUTLINE_TOP = 2150
OUTLINE_BOTTOM = 1940
POS_TOL_RELAXED = 4  # encoder tolerance for being "at" relaxed / stretched positions
POS_TOL_STRETCHED = 100
SHOW_OUTLINES = True

def invert(v, home=HOME):
    """Mirror position value around home (e.g., 2247 ↔ 1847)."""
    return 2 * home - v


def add_interval_shapes(fig, df, mask, color):
    """
    Add vertical rectangular outlines for contiguous time intervals
    where `mask` is True. Uses OUTLINE_BOTTOM / OUTLINE_TOP for Y range.
    """
    in_segment = False
    start = None

    for t, active in zip(df["t_sec"], mask):
        if active and not in_segment:
            in_segment = True
            start = t
        elif not active and in_segment:
            end = t
            fig.add_shape(
                type="rect",
                x0=start,
                x1=end,
                y0=OUTLINE_BOTTOM,
                y1=OUTLINE_TOP,
                fillcolor=color,
                opacity=0.15,
                line=dict(color=color, width=1),
                layer="below",
            )
            in_segment = False

    # Close any open segment that runs to the end of the data
    if in_segment:
        end = df["t_sec"].iloc[-1]
        fig.add_shape(
            type="rect",
            x0=start,
            x1=end,
            y0=OUTLINE_BOTTOM,
            y1=OUTLINE_TOP,
            fillcolor=color,
            opacity=0.15,
            line=dict(color=color, width=1),
            layer="below",
        )


def main():
    # --------------------------
    # Validate argument
    # --------------------------
    if len(sys.argv) != 2:
        print("Usage: python log_viz.py <path_to_csv>")
        sys.exit(1)

    csv_path = sys.argv[1]

    if not os.path.exists(csv_path):
        print(f"Error: Path does not exist: {csv_path}")
        sys.exit(1)
    if not os.path.isfile(csv_path):
        print(f"Error: Not a file: {csv_path}")
        sys.exit(1)

    # --------------------------
    # Load CSV
    # --------------------------
    df = pd.read_csv(csv_path)

    # Parse timestamp
    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    except Exception:
        pass

    # --------------------------
    # Generate t_sec (seconds since test start)
    # --------------------------
    if "timestamp" in df.columns and pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["t_sec"] = (df["timestamp"] - df["timestamp"].iloc[0]).dt.total_seconds()
    else:
        df["t_sec"] = np.arange(len(df))  # fallback if timestamps are bad

    # --------------------------
    # Motor 1 and mirrored Motor 2
    # --------------------------
    df["M1_target"] = df["target pos (1)"]
    df["M1_pos"]    = df["pos (1)"]

    df["M2_target"] = invert(df["target pos (2)"])
    df["M2_pos"]    = invert(df["pos (2)"])

    # Masks for relaxed and stretched states (M3 + M4)
    # Relaxed: both motors at relaxed targets, both actual positions within ±POS_TOL,
    # and M1/M2 at home target position.
    relaxed_targets = (
        (df["target pos (3)"] == M3_RELAXED) &
        (df["target pos (4)"] == M4_RELAXED)
    )
    relaxed_pos_ok = (
        (df["pos (3)"] - M3_RELAXED).abs() <= POS_TOL_RELAXED
    ) & (
        (df["pos (4)"] - M4_RELAXED).abs() <= POS_TOL_RELAXED
    )
    target_home_12 = (
        (df["target pos (1)"] == HOME) &
        (df["target pos (2)"] == HOME)
    )
    home_12 = (
        ((df["pos (1)"] - HOME).abs() <= POS_TOL_RELAXED) &
        ((df["pos (2)"] - HOME).abs() <= POS_TOL_RELAXED)
    )
    relaxed_mask = relaxed_targets & relaxed_pos_ok & home_12 & target_home_12

    # Stretched: exactly one motor is in stretched state (target),
    # and the stretched motor's actual position is within ±POS_TOL.
    stretched_targets = (
        (df["target pos (3)"] == M3_STRETCHED) |
        (df["target pos (4)"] == M4_STRETCHED)
    )
    stretched_pos_ok = (
        (df["target pos (3)"] == M3_STRETCHED) &
        ((df["pos (3)"] - M3_STRETCHED).abs() <= POS_TOL_STRETCHED)
    ) | (
        (df["target pos (4)"] == M4_STRETCHED) &
        ((df["pos (4)"] - M4_STRETCHED).abs() <= POS_TOL_STRETCHED)
    )
    stretched_mask = stretched_targets & stretched_pos_ok

    # --------------------------
    # Create interactive Plotly figure
    # --------------------------
    fig = go.Figure()

    fig.add_trace(go.Scatter(x=df["t_sec"], y=df["M1_target"], mode="lines", name="Motor 1 Target", line=dict(dash="solid")))
    fig.add_trace(go.Scatter(x=df["t_sec"], y=df["M1_pos"], mode="lines", name="Motor 1 Position", line=dict(dash="solid")))

    fig.add_trace(go.Scatter(x=df["t_sec"], y=df["M2_target"], mode="lines", name="Motor 2 Target (mirrored)", line=dict(dash="dash")))
    fig.add_trace(go.Scatter(x=df["t_sec"], y=df["M2_pos"], mode="lines", name="Motor 2 Position (mirrored)", line=dict(dash="solid")))

    # Legend entries for relaxed / stretched outlines
    if SHOW_OUTLINES:
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode="lines",
            line=dict(color="green", width=3),
            name="Relaxed Region"
        ))
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode="lines",
            line=dict(color="red", width=3),
            name="Stretched Region"
        ))

    # Outlines for relaxed (green) and stretched (red) sections based on M3/M4 targets
    if SHOW_OUTLINES:
        add_interval_shapes(fig, df, relaxed_mask, "green")
        add_interval_shapes(fig, df, stretched_mask, "red")

    # --------------------------
    # Layout & Display
    # --------------------------
    fig.update_layout(
        title="Motor 1 & Mirrored Motor 2",
        xaxis_title="Time (seconds)",
        yaxis_title="Position",
        hovermode="x unified",
        legend_title_text="Series",
        plot_bgcolor="#ffffff",
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="gray",
        gridwidth=1,
        griddash="dot"
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor="gray",
        gridwidth=1,
        griddash="dot"
    )

    fig.show()


if __name__ == "__main__":
    main()