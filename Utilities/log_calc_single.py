#!/usr/bin/env python3
import sys
import os
import pandas as pd
import numpy as np

HOME = 2047
HOME_TOL = 5              # how close M5 must be to HOME to count as "holding home"
M3_RELAXED = 1747
M4_RELAXED = 2347
M3_STRETCHED = 2147
M4_STRETCHED = 1947
POS_TOL_RELAXED = 4
POS_TOL_STRETCHED = 100
MIN_SEGMENT_SAMPLES = 10  # ignore very short segments (noise)


def find_segments(mask_series: pd.Series):
    """Return contiguous [start_idx, end_idx] index ranges where mask_series is True."""
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
        print("Usage: python log_calc_single.py <path_to_csv>")
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
            pass

    if "timestamp" in df.columns and pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["t_sec"] = (df["timestamp"] - df["timestamp"].iloc[0]).dt.total_seconds()
    else:
        df["t_sec"] = np.arange(len(df), dtype=float)

    # --------------------------
    # Phase 2 detection: M5 holding home
    # --------------------------
    target_home_5 = df["target pos (5)"] == HOME
    pos_home_5 = (df["pos (5)"] - HOME).abs() <= HOME_TOL

    # In phase 2 we expect M5 to hold home while M3/M4 move
    phase2_mask = target_home_5  # you can also add & pos_home_5 if you want stricter filtering

    raw_segments = find_segments(phase2_mask)

    # Filter very short segments
    segments = []
    for start_idx, end_idx in raw_segments:
        length = end_idx - start_idx + 1
        if length >= MIN_SEGMENT_SAMPLES:
            segments.append((start_idx, end_idx))

    # Sort segments by start index (== time) just in case
    segments = sorted(segments, key=lambda x: x[0])

    if not segments:
        print("No phase-2 segments detected (check HOME_TOL / MIN_SEGMENT_SAMPLES).")
        sys.exit(0)

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

    print("Detected phase-2 segments:")

    def print_subsegment(label: str, seg_slice: pd.DataFrame):
        t_start = seg_slice["t_sec"].iloc[0]
        t_end = seg_slice["t_sec"].iloc[-1]
        n_samples = len(seg_slice)
        m5_avg = seg_slice["pos (5)"].mean()
        print(
            f"    - {label}: samples={n_samples}, "
            f"t_sec=[{t_start:.3f}, {t_end:.3f}], "
            f"M5_avg={m5_avg:.2f}"
        )

    all_m3_stretched = []
    all_m3_relaxed = []
    all_m4_stretched = []
    all_m4_relaxed = []

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

        subsegments_this_seg = []  # (label, seg_slice)

        # M3 stretched + following relaxed
        for (ls, le) in m3_stretch_segments:
            g_start = start_idx + ls
            g_end = start_idx + le
            s = df.iloc[g_start:g_end + 1]
            subsegments_this_seg.append(("M3 stretched", s))
            all_m3_stretched.append(s)

            for (rs, re) in relaxed_segments:
                if rs > le:
                    rg_start = start_idx + rs
                    rg_end = start_idx + re
                    rslice = df.iloc[rg_start:rg_end + 1]
                    subsegments_this_seg.append(("M3 relaxed", rslice))
                    all_m3_relaxed.append(rslice)
                    break

        # M4 stretched + following relaxed
        for (ls, le) in m4_stretch_segments:
            g_start = start_idx + ls
            g_end = start_idx + le
            s = df.iloc[g_start:g_end + 1]
            subsegments_this_seg.append(("M4 stretched", s))
            all_m4_stretched.append(s)

            for (rs, re) in relaxed_segments:
                if rs > le:
                    rg_start = start_idx + rs
                    rg_end = start_idx + re
                    rslice = df.iloc[rg_start:rg_end + 1]
                    subsegments_this_seg.append(("M4 relaxed", rslice))
                    all_m4_relaxed.append(rslice)
                    break

        # Order subsegments by time within this segment
        subsegments_this_seg.sort(key=lambda item: item[1]["t_sec"].iloc[0])

        for label, seg_slice in subsegments_this_seg:
            print_subsegment(label, seg_slice)

    # --------------------------
    # Global averages across all segments
    # --------------------------
    def avg_group(name: str, group):
        if not group:
            print(f"  {name}: no samples")
            return None
        concat = pd.concat(group)
        m5 = concat["pos (5)"].mean()
        print(f"  {name}: M5_avg={m5:.2f}")
        return m5

    print("\nTotal averages across all segments:")
    m3_stretched_avg = avg_group("M3 stretched", all_m3_stretched)
    m3_relaxed_avg = avg_group("M3 relaxed", all_m3_relaxed)
    m4_stretched_avg = avg_group("M4 stretched", all_m4_stretched)
    m4_relaxed_avg = avg_group("M4 relaxed", all_m4_relaxed)

    # --------------------------
    # Position deviation for motor 5
    # --------------------------
    print("\nPosition deviation (Motor 5):")
    if m3_stretched_avg is not None and m4_stretched_avg is not None:
        d_stretched = abs(m3_stretched_avg - m4_stretched_avg)
        print(f"  Stretched deviation: {d_stretched:.2f}")
    else:
        print("  Stretched deviation: insufficient data")

    if m3_relaxed_avg is not None and m4_relaxed_avg is not None:
        d_relaxed = abs(m3_relaxed_avg - m4_relaxed_avg)
        print(f"  Relaxed deviation: {d_relaxed:.2f}")
    else:
        print("  Relaxed deviation: insufficient data")

    print("Done.")


if __name__ == "__main__":
    main()
