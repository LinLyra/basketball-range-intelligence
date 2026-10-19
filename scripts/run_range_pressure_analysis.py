#!/usr/bin/env python3
"""Download/cache a documented peer cohort and build the Curry report assets."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from bie.data_loader import load_local_shots, load_nba_api_shots, save_processed
from bie.range_pressure import (
    PROFILE_METRICS,
    add_range_features,
    add_peer_percentiles,
    bootstrap_range_profile,
    build_peer_benchmark,
)
from bie.shot_chart import plot_shot_chart, plot_shot_density


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "figures" / "curry"
REPORTS = ROOT / "reports" / "curry"
COHORT_PATH = ROOT / "configs" / "peer_cohort.csv"


def slug(text: str) -> str:
    return "_".join(text.lower().replace(".", "").split())


def get_shots(name: str, player_id: int, season: str, offline: bool) -> pd.DataFrame:
    path = RAW / f"{slug(name)}_{season}.csv"
    if path.exists():
        return load_local_shots(path)
    if offline:
        raise FileNotFoundError(f"Offline mode: missing cache {path}")
    shots = load_nba_api_shots(player_id, season)
    save_processed(shots, path)
    return shots


def plot_peer_profiles(scored: pd.DataFrame, output: Path) -> None:
    plot = scored.sort_values("range_pressure_index")
    colors = ["#f5c542" if p == "Stephen Curry" else "#6d7a8a" for p in plot["player_name"]]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.barh(plot["player_name"], plot["range_pressure_index"], color=colors)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Peer-normalized index (0–100)")
    ax.set_title("2024–25 Shooting Range Pressure Profile\nDocumented comparison cohort")
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_curry_shot_assets(shots: pd.DataFrame) -> None:
    fig, _ = plot_shot_chart(
        shots,
        "Stephen Curry — 2024–25 Regular-Season Shot Chart",
        FIGURES / "01_curry_shot_chart.png",
    )
    plt.close(fig)
    fig, _ = plot_shot_density(
        shots,
        "Stephen Curry — 2024–25 Shot Density",
        FIGURES / "02_curry_shot_density.png",
    )
    plt.close(fig)

    ranged = add_range_features(shots)
    labels = ["<23.75 ft", "23.75–27.9 ft", "28–29.9 ft", "30+ ft"]
    categories = pd.cut(
        ranged["distance_from_rim_ft"],
        bins=[0, 23.75, 28, 30, float("inf")],
        labels=labels,
        right=False,
    )
    counts = categories.value_counts(sort=False)
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    bars = ax.bar(counts.index.astype(str), counts.values, color=["#8794a3", "#4f6b87", "#32659a", "#f5c542"])
    ax.bar_label(bars, padding=3)
    ax.set_ylabel("Field-goal attempts")
    ax.set_title("Curry 2024–25 Attempts by Distance Band")
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(FIGURES / "03_curry_range_distribution.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def write_report(scored: pd.DataFrame, intervals: pd.DataFrame, season: str) -> None:
    curry_row = scored.loc[scored["player_name"] == "Stephen Curry"]
    if curry_row.empty:
        raise ValueError("Stephen Curry is missing from the peer cohort")
    curry = curry_row.iloc[0]
    rank = int(curry_row.index[0]) + 1
    metric_rows = []
    for metric in PROFILE_METRICS:
        row = intervals.loc[intervals["metric"] == metric].iloc[0]
        metric_rows.append(
            f"| {metric} | {row['estimate']:.3f} | "
            f"[{row['ci_low']:.3f}, {row['ci_high']:.3f}] |"
        )
    report = f"""# Stephen Curry — Shooting Range Pressure, {season}

## What this report measures

This case study measures the range, frequency and observed efficiency of public
shot-location data. It does **not** measure true defensive gravity, off-ball
attention, defender displacement or teammate openness.

## Result

Curry ranks **{rank} of {len(scored)}** in the documented comparison cohort,
with a peer-normalized Range Pressure Index of **{curry['range_pressure_index']:.1f}/100**.
The index is the equal-weight mean of empirical percentiles for three-point rate,
deep-three rate, 30+ foot rate, average shot distance and shrinkage-adjusted
deep-three accuracy. It is descriptive and cohort-dependent, not a universal scale.

| Metric | Estimate | Attempt-bootstrap 95% interval |
|---|---:|---:|
{chr(10).join(metric_rows)}

## Evidence boundaries

- A shot chart records attempts, not where defenders stood.
- Deep-shot accuracy is partially pooled toward a 35% prior to reduce small-sample noise.
- Attempt-level bootstrap intervals describe sampling variability but do not account for
  possession, game-state or opponent dependence.
- The peer cohort is curated and small; results must not be described as league percentiles.
- The next research step is a tracking or adjusted on/off design that measures downstream
  defensive and teammate effects.

## Reproducibility

- Season: `{season}` regular season
- Report generated (UTC): `{datetime.now(timezone.utc).isoformat()}`
- Cohort definition: `configs/peer_cohort.csv`
- Cached raw data: `data/raw/`
- Cache timestamps: `data/raw/source_manifest.csv`
- Machine-readable results: `data/processed/`
"""
    (REPORTS / "range_pressure_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default="2024-25")
    parser.add_argument("--offline", action="store_true", help="Require existing cached CSV files")
    parser.add_argument("--bootstrap", type=int, default=2_000)
    args = parser.parse_args()

    for path in (RAW, PROCESSED, FIGURES, REPORTS):
        path.mkdir(parents=True, exist_ok=True)

    cohort = pd.read_csv(COHORT_PATH)
    player_shots = {}
    manifest_rows = []
    for row in cohort.itertuples(index=False):
        print(f"Loading {row.player_name} ({row.player_id})...")
        player_shots[row.player_name] = get_shots(
            row.player_name, int(row.player_id), args.season, args.offline
        )
        cache_path = RAW / f"{slug(row.player_name)}_{args.season}.csv"
        manifest_rows.append(
            {
                "player_name": row.player_name,
                "player_id": int(row.player_id),
                "season": args.season,
                "source": "NBA Stats via nba_api",
                "cache_path": str(cache_path.relative_to(ROOT)),
                "cache_modified_utc": datetime.fromtimestamp(
                    cache_path.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
                "attempts": len(player_shots[row.player_name]),
            }
        )

    pd.DataFrame(manifest_rows).to_csv(RAW / "source_manifest.csv", index=False)

    benchmark = build_peer_benchmark(player_shots)
    scored = add_peer_percentiles(benchmark)
    curry_intervals = bootstrap_range_profile(
        player_shots["Stephen Curry"], n_boot=args.bootstrap
    )

    benchmark.to_csv(PROCESSED / "peer_range_profiles.csv", index=False)
    scored.to_csv(PROCESSED / "peer_range_pressure_rankings.csv", index=False)
    curry_intervals.to_csv(PROCESSED / "curry_range_profile_intervals.csv", index=False)
    plot_curry_shot_assets(player_shots["Stephen Curry"])
    plot_peer_profiles(scored, FIGURES / "04_peer_range_pressure.png")
    write_report(scored, curry_intervals, args.season)
    print(scored[["player_name", "range_pressure_index"]].to_string(index=False))


if __name__ == "__main__":
    main()
