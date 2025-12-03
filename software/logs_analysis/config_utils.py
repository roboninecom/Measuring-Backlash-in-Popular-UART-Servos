from dataclasses import dataclass
import json
import os
from typing import Dict, List

import pandas as pd


@dataclass
class MotorConfig:
    motor_id: int
    label: str
    relaxed_target: float
    relaxed_tolerance: float
    stretched_target: float
    stretched_tolerance: float


@dataclass
class AnalysisConfig:
    home_position: float
    home_tolerance: float
    home_motor_ids: List[int]
    require_home_position_match: bool
    report_motor_ids: List[int]
    min_segment_samples: int
    actuated_motors: List[MotorConfig]


def target_col(motor_id: int) -> str:
    return f"target pos ({motor_id})"


def pos_col(motor_id: int) -> str:
    return f"pos ({motor_id})"


def ensure_columns(df: pd.DataFrame, columns: List[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise KeyError(f"Missing columns in CSV: {', '.join(missing)}")


def _extract_motor_ids(data: Dict, key: str) -> List[int]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"Config field '{key}' must be a non-empty list.")
    result: List[int] = []
    seen = set()
    for raw_id in value:
        try:
            motor_id = int(raw_id)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Motor id '{raw_id}' in '{key}' is invalid.") from exc
        if motor_id not in seen:
            seen.add(motor_id)
            result.append(motor_id)
    return result


def load_config(config_path: str) -> AnalysisConfig:
    if not os.path.exists(config_path):
        raise ValueError(f"Config file not found: {config_path}")
    if not os.path.isfile(config_path):
        raise ValueError(f"Config path is not a file: {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as fp:
            raw = json.load(fp)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    try:
        home_position = float(raw["home_position"])
    except KeyError as exc:
        raise ValueError("Config is missing 'home_position'.") from exc

    home_motor_ids = _extract_motor_ids(raw, "home_motor_ids")

    home_tolerance = float(raw.get("home_tolerance", 0))
    require_home_position_match = bool(raw.get("require_home_position_match", False))
    report_motor_ids = raw.get("report_motor_ids")
    if report_motor_ids:
        report_motor_ids = _extract_motor_ids(raw, "report_motor_ids")
    else:
        report_motor_ids = list(home_motor_ids)

    min_segment_samples = int(raw.get("min_segment_samples", 1))
    if min_segment_samples <= 0:
        raise ValueError("'min_segment_samples' must be a positive integer.")

    motors_raw = raw.get("actuated_motors")
    if not isinstance(motors_raw, list) or not motors_raw:
        raise ValueError("Config must include at least one entry in 'actuated_motors'.")

    actuated_motors: List[MotorConfig] = []
    for entry in motors_raw:
        try:
            motor_id = int(entry["motor_id"])
            relaxed_target = float(entry["relaxed_target"])
            relaxed_tolerance = float(entry["relaxed_tolerance"])
            stretched_target = float(entry["stretched_target"])
            stretched_tolerance = float(entry["stretched_tolerance"])
        except KeyError as exc:
            raise ValueError(f"Actuated motor entry missing field: {exc.args[0]}") from exc
        except (TypeError, ValueError) as exc:
            raise ValueError("Actuated motor entry includes invalid numeric values.") from exc

        label = entry.get("label") or f"M{motor_id}"
        actuated_motors.append(
            MotorConfig(
                motor_id=motor_id,
                label=label,
                relaxed_target=relaxed_target,
                relaxed_tolerance=relaxed_tolerance,
                stretched_target=stretched_target,
                stretched_tolerance=stretched_tolerance,
            )
        )

    if not report_motor_ids:
        raise ValueError("Config must define at least one 'report_motor_id'.")

    return AnalysisConfig(
        home_position=home_position,
        home_tolerance=home_tolerance,
        home_motor_ids=home_motor_ids,
        require_home_position_match=require_home_position_match,
        report_motor_ids=report_motor_ids,
        min_segment_samples=min_segment_samples,
        actuated_motors=actuated_motors,
    )


def build_phase_mask(df: pd.DataFrame, config: AnalysisConfig) -> pd.Series:
    mask = pd.Series(True, index=df.index, dtype=bool)
    for motor_id in config.home_motor_ids:
        mask &= df[target_col(motor_id)] == config.home_position
        if config.require_home_position_match:
            mask &= (df[pos_col(motor_id)] - config.home_position).abs() <= config.home_tolerance
    return mask


def build_relaxed_mask(df: pd.DataFrame, motors: List[MotorConfig]) -> pd.Series:
    mask = pd.Series(True, index=df.index, dtype=bool)
    for motor in motors:
        mask &= df[target_col(motor.motor_id)] == motor.relaxed_target
        mask &= (df[pos_col(motor.motor_id)] - motor.relaxed_target).abs() <= motor.relaxed_tolerance
    return mask


def build_stretch_mask(df: pd.DataFrame, motor: MotorConfig) -> pd.Series:
    mask = df[target_col(motor.motor_id)] == motor.stretched_target
    mask &= (df[pos_col(motor.motor_id)] - motor.stretched_target).abs() <= motor.stretched_tolerance
    return mask


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
