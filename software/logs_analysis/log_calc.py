#!/usr/bin/env python3
import os
import sys
from itertools import combinations
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from config_utils import (
    AnalysisConfig,
    MotorConfig,
    build_phase_mask,
    build_relaxed_mask,
    build_stretch_mask,
    ensure_columns,
    find_segments,
    load_config,
    pos_col,
    target_col,
)


def summarize_measurements(seg_slice: pd.DataFrame, report_motor_ids: List[int]) -> str:
    summaries = []
    for motor_id in report_motor_ids:
        avg = seg_slice[pos_col(motor_id)].mean()
        summaries.append(f"M{motor_id}_avg={avg:.2f}")
    return ", ".join(summaries)


def print_subsegment(label: str, seg_slice: pd.DataFrame, report_motor_ids: List[int]) -> None:
    t_start = seg_slice["t_sec"].iloc[0]
    t_end = seg_slice["t_sec"].iloc[-1]
    n_samples = len(seg_slice)
    measurements = summarize_measurements(seg_slice, report_motor_ids)
    print(
        f"    - {label}: samples={n_samples}, "
        f"t_sec=[{t_start:.3f}, {t_end:.3f}], {measurements}"
    )


def average_positions(slices: List[pd.DataFrame], report_motor_ids: List[int]) -> Optional[Dict[int, float]]:
    if not slices:
        return None
    concat = pd.concat(slices)
    return {motor_id: concat[pos_col(motor_id)].mean() for motor_id in report_motor_ids}


def analyze_log(df: pd.DataFrame, config: AnalysisConfig) -> None:
    required_columns = set()
    for motor_id in config.home_motor_ids:
        required_columns.add(target_col(motor_id))
        required_columns.add(pos_col(motor_id))
    for motor_id in config.report_motor_ids:
        required_columns.add(pos_col(motor_id))
    for motor in config.actuated_motors:
        required_columns.add(target_col(motor.motor_id))
        required_columns.add(pos_col(motor.motor_id))
    ensure_columns(df, sorted(required_columns))

    if "timestamp" in df.columns:
        try:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        except Exception:
            pass

    if "timestamp" in df.columns and pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["t_sec"] = (df["timestamp"] - df["timestamp"].iloc[0]).dt.total_seconds()
    else:
        df["t_sec"] = np.arange(len(df), dtype=float)

    phase_mask = build_phase_mask(df, config)
    raw_segments = find_segments(phase_mask)
    segments = [
        (start_idx, end_idx)
        for (start_idx, end_idx) in raw_segments
        if (end_idx - start_idx + 1) >= config.min_segment_samples
    ]

    if not segments:
        print("No phase-2 segments detected (check config thresholds).")
        return

    relaxed_mask = build_relaxed_mask(df, config.actuated_motors)
    stretch_masks = {motor.motor_id: build_stretch_mask(df, motor) for motor in config.actuated_motors}
    global_groups: Dict[str, Dict[str, List[pd.DataFrame]]] = {
        motor.label: {"stretched": [], "relaxed": []} for motor in config.actuated_motors
    }

    print("Detected phase-2 segments:")
    for seg_id, (start_idx, end_idx) in enumerate(segments, start=1):
        seg = df.iloc[start_idx:end_idx + 1]
        t_start = seg["t_sec"].iloc[0]
        t_end = seg["t_sec"].iloc[-1]
        n_samples = len(seg)
        print(f"  Segment {seg_id}: samples={n_samples}, t_sec=[{t_start:.3f}, {t_end:.3f}]")

        relaxed_local = relaxed_mask.iloc[start_idx:end_idx + 1].reset_index(drop=True)
        relaxed_segments = find_segments(relaxed_local)

        subsegments: List[tuple] = []
        for motor in config.actuated_motors:
            stretch_local = stretch_masks[motor.motor_id].iloc[start_idx:end_idx + 1].reset_index(drop=True)
            stretch_segments = find_segments(stretch_local)

            for ls, le in stretch_segments:
                global_start = start_idx + ls
                global_end = start_idx + le
                stretch_slice = df.iloc[global_start:global_end + 1]
                label = f"{motor.label} stretched"
                subsegments.append((label, stretch_slice))
                global_groups[motor.label]["stretched"].append(stretch_slice)

                for rs, re in relaxed_segments:
                    if rs > le:
                        r_start = start_idx + rs
                        r_end = start_idx + re
                        relaxed_slice = df.iloc[r_start:r_end + 1]
                        subsegments.append((f"{motor.label} relaxed", relaxed_slice))
                        global_groups[motor.label]["relaxed"].append(relaxed_slice)
                        break

        subsegments.sort(key=lambda item: item[1]["t_sec"].iloc[0])
        for label, seg_slice in subsegments:
            print_subsegment(label, seg_slice, config.report_motor_ids)

    print("\nTotal averages across all segments:")
    avg_cache: Dict[tuple, Optional[Dict[int, float]]] = {}
    for motor in config.actuated_motors:
        for state in ("stretched", "relaxed"):
            groups = global_groups[motor.label][state]
            avg_map = average_positions(groups, config.report_motor_ids)
            avg_cache[(motor.label, state)] = avg_map
            label = f"{motor.label} {state}"
            if avg_map is None:
                print(f"  {label}: no samples")
            else:
                metrics = ", ".join(f"M{mid}_avg={avg:.2f}" for mid, avg in avg_map.items())
                print(f"  {label}: {metrics}")

    print("\nPosition deviation:")
    motor_pairs = list(combinations(config.actuated_motors, 2))
    if not motor_pairs:
        print("  Requires at least two actuated motors.")
    else:
        for state in ("stretched", "relaxed"):
            for m1, m2 in motor_pairs:
                avg1 = avg_cache.get((m1.label, state))
                avg2 = avg_cache.get((m2.label, state))
                if not avg1 or not avg2:
                    print(f"  {state.title()} ({m1.label} vs {m2.label}): insufficient data")
                    continue
                diffs = [
                    f"M{mid}_dev={abs(avg1[mid] - avg2[mid]):.2f}"
                    for mid in config.report_motor_ids
                ]
                diff_text = ", ".join(diffs)
                print(f"  {state.title()} ({m1.label} vs {m2.label}): {diff_text}")

    print("Done.")


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python log_calc.py <config.json> <path_to_csv>")
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

    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:
        print(f"Error reading CSV: {exc}")
        sys.exit(1)

    try:
        analyze_log(df, config)
    except KeyError as exc:
        print(f"Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
