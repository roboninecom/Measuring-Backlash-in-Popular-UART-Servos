#!/usr/bin/env python3
import sys
import os
import pandas as pd
import numpy as np

HOME = 2047
HOME_TOL = 5              # how close M1/M2 must be to HOME to count as "holding home"
M3_RELAXED = 1747
M4_RELAXED = 2347
M3_STRETCHED = 2247
M4_STRETCHED = 1847
POS_TOL_RELAXED = 4
POS_TOL_STRETCHED = 100
MIN_SEGMENT_SAMPLES = 10  # ignore very short segments (noise)


def find_segments(mask_series):
    """
    Find contiguous [start_idx, end_idx] index ranges where mask_series is True.
    Returns a list of (start_idx, end_idx) tuples in index order.
    """
    segments = []
    in_segment = False
    start_idx = None

    arr = mask_series.to_numpy()
    n = len(arr)

    for i, active in enumerate(arr):
        if active and not in_segment:
            in_segment = True
            start_idx = i
        elif not active and in_segment:
            segments.append((start_idx, i - 1))
            in_segment = False

    if in_segment and start_idx is not None:
        segments.append((start_idx, n - 1))

    return segments


def main():
    # --------------------------
    # Validate argument
    # --------------------------
    if len(sys.argv) != 2:
        print("Usage: python log_calc.py <path_to_csv>")
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
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        sys.exit(1)

    # --------------------------
    # Parse timestamp and t_sec
    # --------------------------
    if "timestamp" in df.columns:
        try:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        except Exception:
            # leave as-is if parsing fails
            pass

    if "timestamp" in df.columns and pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["t_sec"] = (df["timestamp"] - df["timestamp"].iloc[0]).dt.total_seconds()
    else:
        df["t_sec"] = np.arange(len(df), dtype=float)

    # --------------------------
    # Phase 2 detection: M1 and M2 holding home
    # --------------------------
    # Targets at home
    target_home_12 = (
        (df["target pos (1)"] == HOME) &
        (df["target pos (2)"] == HOME)
    )

    # Actual positions close to home
    pos_home_12 = (
        (df["pos (1)"] - HOME).abs() <= HOME_TOL
    ) & (
        (df["pos (2)"] - HOME).abs() <= HOME_TOL
    )

    # Phase-2 mask: M1 & M2 holding home
    phase2_mask = target_home_12# & pos_home_12

    # --------------------------
    # Find phase-2 segments
    # --------------------------
    raw_segments = find_segments(phase2_mask)

    # Optionally filter out very short segments
    segments = []
    for start_idx, end_idx in raw_segments:
        length = end_idx - start_idx + 1
        if length >= MIN_SEGMENT_SAMPLES:
            segments.append((start_idx, end_idx))

    # Sort segments by start index ascending
    segments = sorted(segments, key=lambda x: x[0])

    if not segments:
        print("No phase-2 segments detected (check HOME_TOL / MIN_SEGMENT_SAMPLES).")
        sys.exit(0)

    # --------------------------
    # Build segment_id column
    # --------------------------
    segment_id = np.zeros(len(df), dtype=int)
    for seg_id, (start_idx, end_idx) in enumerate(segments, start=1):
        segment_id[start_idx:end_idx + 1] = seg_id

    df["segment_id"] = segment_id

    # --------------------------
    # Relaxed / stretched masks for M3 & M4 (whole log)
    # --------------------------
    relaxed_targets = (
        (df["target pos (3)"] == M3_RELAXED) &
        (df["target pos (4)"] == M4_RELAXED)
    )
    relaxed_pos_ok = (
        (df["pos (3)"] - M3_RELAXED).abs() <= POS_TOL_RELAXED
    ) & (
        (df["pos (4)"] - M4_RELAXED).abs() <= POS_TOL_RELAXED
    )
    relaxed_mask = relaxed_targets & relaxed_pos_ok

    m3_stretch_mask = (
        (df["target pos (3)"] == M3_STRETCHED) &
        ((df["pos (3)"] - M3_STRETCHED).abs() <= POS_TOL_STRETCHED)
    )
    m4_stretch_mask = (
        (df["target pos (4)"] == M4_STRETCHED) &
        ((df["pos (4)"] - M4_STRETCHED).abs() <= POS_TOL_STRETCHED)
    )

    # --------------------------
    # Print segment + subsegment summary
    # --------------------------
    print("Detected phase-2 segments:")

    def print_subsegment(label, seg_slice):
        t_start = seg_slice["t_sec"].iloc[0]
        t_end = seg_slice["t_sec"].iloc[-1]
        n_samples = len(seg_slice)
        m1_avg = seg_slice["pos (1)"].mean()
        m2_avg = seg_slice["pos (2)"].mean()
        print(
            f"    - {label}: samples={n_samples}, "
            f"t_sec=[{t_start:.3f}, {t_end:.3f}], "
            f"M1_avg={m1_avg:.2f}, M2_avg={m2_avg:.2f}"
        )

    for seg_id, (start_idx, end_idx) in enumerate(segments, start=1):
        seg = df.iloc[start_idx:end_idx + 1]
        t_start = seg["t_sec"].iloc[0]
        t_end = seg["t_sec"].iloc[-1]
        n_samples = len(seg)
        print(f"  Segment {seg_id}: samples={n_samples}, t_sec=[{t_start:.3f}, {t_end:.3f}]")

        # Local masks within this segment
        m3_stretch_local = m3_stretch_mask[start_idx:end_idx + 1].reset_index(drop=True)
        m4_stretch_local = m4_stretch_mask[start_idx:end_idx + 1].reset_index(drop=True)
        relaxed_local = relaxed_mask[start_idx:end_idx + 1].reset_index(drop=True)

        m3_stretch_segments = find_segments(m3_stretch_local)
        m4_stretch_segments = find_segments(m4_stretch_local)
        relaxed_segments = find_segments(relaxed_local)

        subsegments = []

        # For each M3 stretched segment, find the first relaxed segment that starts after it
        for (ls, le) in m3_stretch_segments:
            global_start = start_idx + ls
            global_end = start_idx + le
            sub = df.iloc[global_start:global_end + 1]
            subsegments.append(("M3 stretched", sub))

            for (rs, re) in relaxed_segments:
                if rs > le:
                    r_global_start = start_idx + rs
                    r_global_end = start_idx + re
                    r_sub = df.iloc[r_global_start:r_global_end + 1]
                    subsegments.append(("M3 relaxed", r_sub))
                    break

        # For each M4 stretched segment, find the first relaxed segment that starts after it
        for (ls, le) in m4_stretch_segments:
            global_start = start_idx + ls
            global_end = start_idx + le
            sub = df.iloc[global_start:global_end + 1]
            subsegments.append(("M4 stretched", sub))

            for (rs, re) in relaxed_segments:
                if rs > le:
                    r_global_start = start_idx + rs
                    r_global_end = start_idx + re
                    r_sub = df.iloc[r_global_start:r_global_end + 1]
                    subsegments.append(("M4 relaxed", r_sub))
                    break

        # Order subsegments by start time (ascending)
        subsegments.sort(key=lambda item: item[1]["t_sec"].iloc[0])

        for label, seg_slice in subsegments:
            print_subsegment(label, seg_slice)

    # --------------------------
    # Global averages across all segments
    # --------------------------
    all_m3_stretched = []
    all_m3_relaxed = []
    all_m4_stretched = []
    all_m4_relaxed = []

    for label, seg_slice in subsegments:
        if label == "M3 stretched":
            all_m3_stretched.append(seg_slice)
        elif label == "M3 relaxed":
            all_m3_relaxed.append(seg_slice)
        elif label == "M4 stretched":
            all_m4_stretched.append(seg_slice)
        elif label == "M4 relaxed":
            all_m4_relaxed.append(seg_slice)

    def avg_group(name, group):
        if not group:
            print(f"  {name}: no samples")
            return
        concat = pd.concat(group)
        m1 = concat["pos (1)"].mean()
        m2 = concat["pos (2)"].mean()
        print(f"  {name}: M1_avg={m1:.2f}, M2_avg={m2:.2f}")

    print("Total averages across all segments:")
    avg_group("M3 stretched", all_m3_stretched)
    avg_group("M3 relaxed", all_m3_relaxed)
    avg_group("M4 stretched", all_m4_stretched)
    avg_group("M4 relaxed", all_m4_relaxed)

    # --------------------------
    # Position deviation calculations
    # --------------------------
    def deviation(name, g1, g2):
        if not g1 or not g2:
            print(f"  {name}: insufficient data")
            return
        c1 = pd.concat(g1)
        c2 = pd.concat(g2)
        m1_dev = abs(c1["pos (1)"].mean() - c2["pos (1)"].mean())
        m2_dev = abs(c1["pos (2)"].mean() - c2["pos (2)"].mean())
        print(f"  {name}: M1_dev={m1_dev:.2f}, M2_dev={m2_dev:.2f}")

    print("Position deviation:")
    deviation("Stretched deviation", all_m3_stretched, all_m4_stretched)
    deviation("Relaxed deviation", all_m3_relaxed, all_m4_relaxed)

    print("Done.")


if __name__ == "__main__":
    main()
