"""Longitudinal features and uncertainty for a player-intelligence report."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .range_pressure import add_range_features


DISTANCE_BANDS = ("0–9 ft", "10–15 ft", "16–22 ft", "3PT <28 ft", "28–29 ft", "30+ ft")


def season_label_start(season: str) -> int:
    return int(str(season).split("-")[0])


def summarize_player_season(shots: pd.DataFrame, *, player_name: str, season: str, season_type: str) -> pd.Series:
    df = add_range_features(shots)
    threes = df[df["is_three"]]
    deep = df[df["is_deep_three"]]
    very_deep = df[df["is_very_deep"]]
    games = max(int(df["GAME_ID"].nunique()) if "GAME_ID" in df else 1, 1)
    z = 1.96

    def wilson(makes: int, attempts: int) -> tuple[float, float]:
        if attempts == 0:
            return np.nan, np.nan
        p = makes / attempts
        den = 1 + z**2 / attempts
        centre = (p + z**2 / (2 * attempts)) / den
        half = z * np.sqrt(p * (1 - p) / attempts + z**2 / (4 * attempts**2)) / den
        return centre - half, centre + half

    deep_low, deep_high = wilson(int(deep["SHOT_MADE_FLAG"].sum()), len(deep))
    return pd.Series({
        "player_name": player_name, "season": season,
        "season_start": season_label_start(season), "season_type": season_type,
        "games_with_fga": games, "fga": len(df), "fga_per_game": len(df) / games,
        "fg_pct": df["SHOT_MADE_FLAG"].mean(), "three_attempts": len(threes),
        "three_rate": df["is_three"].mean(), "three_attempts_per_game": len(threes) / games,
        "three_fg_pct": threes["SHOT_MADE_FLAG"].mean() if len(threes) else np.nan,
        "deep_attempts": len(deep), "deep_rate": df["is_deep_three"].mean(),
        "deep_attempts_per_game": len(deep) / games,
        "deep_fg_pct": deep["SHOT_MADE_FLAG"].mean() if len(deep) else np.nan,
        "deep_fg_ci_low": deep_low, "deep_fg_ci_high": deep_high,
        "very_deep_attempts": len(very_deep), "very_deep_rate": df["is_very_deep"].mean(),
        "very_deep_attempts_per_game": len(very_deep) / games,
        "very_deep_fg_pct": very_deep["SHOT_MADE_FLAG"].mean() if len(very_deep) else np.nan,
        "avg_shot_distance_ft": df["distance_from_rim_ft"].mean(),
    })


def distance_band_table(shots: pd.DataFrame, *, season: str, season_type: str) -> pd.DataFrame:
    df = add_range_features(shots)
    distance, three = df["distance_from_rim_ft"], df["is_three"]
    conditions = [distance < 10, distance.between(10, 15.999), distance.between(16, 22.999),
                  three & (distance < 28), distance.between(28, 29.999), distance >= 30]
    df["distance_band"] = np.select(conditions, DISTANCE_BANDS, default="Other")
    out = (df[df["distance_band"] != "Other"].groupby("distance_band", observed=False)
           .agg(attempts=("SHOT_MADE_FLAG", "size"), makes=("SHOT_MADE_FLAG", "sum"))
           .reindex(DISTANCE_BANDS, fill_value=0).reset_index())
    out["fg_pct"] = out["makes"].div(out["attempts"].replace(0, np.nan))
    out["attempt_share"] = out["attempts"] / max(len(df), 1)
    out.insert(0, "season_type", season_type); out.insert(0, "season", season)
    return out


def add_season_peer_percentiles(summary: pd.DataFrame) -> pd.DataFrame:
    """Percentiles within the documented available-player cohort for each season."""
    out = summary.copy()
    metrics = ["three_rate", "deep_rate", "very_deep_rate", "avg_shot_distance_ft"]
    for metric in metrics:
        out[f"{metric}_peer_pctile"] = out.groupby(["season", "season_type"])[metric].rank(
            method="average", pct=True
        ) * 100
    out["range_pressure_peer_pctile"] = out[[f"{x}_peer_pctile" for x in metrics]].mean(axis=1)
    out["peer_n"] = out.groupby(["season", "season_type"])["player_name"].transform("size")
    return out


def detect_mean_shift(series: pd.Series, min_segment: int = 3) -> dict[str, float | int] | None:
    """Transparent single change-point: split minimizing within-segment SSE."""
    y = pd.Series(series).dropna().to_numpy(float)
    if len(y) < min_segment * 2:
        return None
    candidates = []
    for split in range(min_segment, len(y) - min_segment + 1):
        left, right = y[:split], y[split:]
        sse = ((left - left.mean()) ** 2).sum() + ((right - right.mean()) ** 2).sum()
        candidates.append((sse, split, left.mean(), right.mean()))
    sse, split, before, after = min(candidates)
    return {"split_index": split, "before_mean": before, "after_mean": after, "sse": sse}
