"""Transparent shot-range metrics for the Curry case study.

The outputs in this module describe shooting range and volume. They are not a
measurement of defensive attention or off-ball gravity, which requires tracking
or a stronger causal proxy.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data_loader import validate_shot_columns


PROFILE_METRICS = (
    "three_rate",
    "deep_three_rate",
    "very_deep_rate",
    "avg_shot_distance_ft",
    "deep_three_eb_fg_pct",
)


@dataclass(frozen=True)
class RangeDefinitions:
    deep_three_ft: float = 28.0
    very_deep_ft: float = 30.0
    prior_makes: float = 35.0
    prior_attempts: float = 100.0


def add_range_features(
    shots: pd.DataFrame,
    definitions: RangeDefinitions = RangeDefinitions(),
) -> pd.DataFrame:
    validate_shot_columns(shots)
    out = shots.copy()
    out["distance_from_rim_ft"] = np.hypot(out["LOC_X"], out["LOC_Y"]) / 10.0
    out["is_three"] = out["SHOT_TYPE"].astype(str).str.contains("3PT", case=False, na=False)
    out["is_deep_three"] = out["distance_from_rim_ft"] >= definitions.deep_three_ft
    out["is_very_deep"] = out["distance_from_rim_ft"] >= definitions.very_deep_ft
    return out


def summarize_range_profile(
    shots: pd.DataFrame,
    *,
    player_name: str | None = None,
    definitions: RangeDefinitions = RangeDefinitions(),
) -> pd.Series:
    """Summarize one player-season with shrinkage for sparse deep attempts."""
    df = add_range_features(shots, definitions)
    deep = df.loc[df["is_deep_three"]]
    deep_attempts = int(len(deep))
    deep_makes = int(deep["SHOT_MADE_FLAG"].sum())
    eb_deep_fg = (
        deep_makes + definitions.prior_makes
    ) / (
        deep_attempts + definitions.prior_attempts
    )
    return pd.Series(
        {
            "player_name": player_name or "Unknown",
            "attempts": int(len(df)),
            "makes": int(df["SHOT_MADE_FLAG"].sum()),
            "fg_pct": float(df["SHOT_MADE_FLAG"].mean()),
            "three_rate": float(df["is_three"].mean()),
            "deep_three_attempts": deep_attempts,
            "deep_three_rate": float(df["is_deep_three"].mean()),
            "very_deep_rate": float(df["is_very_deep"].mean()),
            "avg_shot_distance_ft": float(df["distance_from_rim_ft"].mean()),
            "deep_three_fg_pct": float(deep["SHOT_MADE_FLAG"].mean()) if deep_attempts else np.nan,
            "deep_three_eb_fg_pct": float(eb_deep_fg),
        }
    )


def bootstrap_range_profile(
    shots: pd.DataFrame,
    *,
    n_boot: int = 2_000,
    confidence: float = 0.95,
    seed: int = 42,
    definitions: RangeDefinitions = RangeDefinitions(),
) -> pd.DataFrame:
    """Attempt-level bootstrap intervals for descriptive profile metrics."""
    df = add_range_features(shots, definitions)
    rng = np.random.default_rng(seed)
    values = {metric: [] for metric in PROFILE_METRICS}
    for _ in range(n_boot):
        idx = rng.integers(0, len(df), len(df))
        profile = summarize_range_profile(df.iloc[idx], definitions=definitions)
        for metric in PROFILE_METRICS:
            values[metric].append(float(profile[metric]))
    alpha = (1.0 - confidence) / 2.0
    point = summarize_range_profile(df, definitions=definitions)
    rows = []
    for metric, samples in values.items():
        rows.append(
            {
                "metric": metric,
                "estimate": float(point[metric]),
                "ci_low": float(np.quantile(samples, alpha)),
                "ci_high": float(np.quantile(samples, 1.0 - alpha)),
                "confidence": confidence,
            }
        )
    return pd.DataFrame(rows)


def build_peer_benchmark(player_shots: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Create one row per peer from identically defined shot charts."""
    if len(player_shots) < 3:
        raise ValueError("A peer benchmark requires at least three players")
    return pd.DataFrame(
        [summarize_range_profile(shots, player_name=name) for name, shots in player_shots.items()]
    )


def add_peer_percentiles(benchmark: pd.DataFrame) -> pd.DataFrame:
    """Add transparent empirical percentiles and their equal-weight mean.

    This is a *peer-normalized Range Pressure Index*, not league-wide gravity.
    Percentiles are only as representative as the documented peer cohort.
    """
    required = {"player_name", *PROFILE_METRICS}
    missing = required.difference(benchmark.columns)
    if missing:
        raise ValueError(f"Benchmark is missing: {sorted(missing)}")
    out = benchmark.copy()
    percentile_columns = []
    for metric in PROFILE_METRICS:
        column = f"{metric}_percentile"
        out[column] = out[metric].rank(method="average", pct=True) * 100.0
        percentile_columns.append(column)
    out["range_pressure_index"] = out[percentile_columns].mean(axis=1)
    return out.sort_values("range_pressure_index", ascending=False).reset_index(drop=True)
