#!/usr/bin/env python3
"""Build a career-long Curry intelligence dataset, figures and research website."""

from __future__ import annotations

import argparse
import html
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bie.career import (add_season_peer_percentiles, detect_mean_shift, distance_band_table,
                        summarize_player_season)
from bie.data_loader import load_local_shots, load_nba_api_shots, save_processed

ROOT = Path(__file__).resolve().parents[1]
RAW, PROCESSED = ROOT / "data/raw/career", ROOT / "data/processed"
FIGURES, REPORTS = ROOT / "figures/curry/career", ROOT / "reports/curry"
COHORT = ROOT / "configs/peer_cohort.csv"
ANNOTATIONS = ROOT / "configs/career_annotations.csv"
CURRY_START = 2009


def seasons(last_start: int) -> list[str]:
    return [f"{year}-{str(year + 1)[-2:]}" for year in range(CURRY_START, last_start + 1)]


def slug(value: str) -> str:
    return "_".join(value.lower().replace(".", "").split())


def cache_path(name: str, season: str, season_type: str) -> Path:
    kind = "regular" if season_type == "Regular Season" else "playoffs"
    return RAW / slug(name) / f"{season}_{kind}.csv"


def get_shots(name: str, player_id: int, season: str, season_type: str, offline: bool):
    path = cache_path(name, season, season_type)
    if path.exists():
        return load_local_shots(path)
    if offline:
        return None
    try:
        frame = load_nba_api_shots(player_id, season, season_type=season_type, retries=2)
    except RuntimeError as exc:
        print(f"SKIP {name} {season} {season_type}: {exc}")
        return None
    save_processed(frame, path)
    return frame


def build_data(last_start: int, offline: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    cohort = pd.read_csv(COHORT)
    summary, bands = [], []
    for player in cohort.itertuples(index=False):
        for season in seasons(last_start):
            # Peer cohort is regular-season; Curry also receives playoff analysis.
            types = ["Regular Season", "Playoffs"] if player.player_name == "Stephen Curry" else ["Regular Season"]
            for season_type in types:
                frame = get_shots(player.player_name, int(player.player_id), season, season_type, offline)
                if frame is None or frame.empty:
                    continue
                summary.append(summarize_player_season(frame, player_name=player.player_name,
                                                       season=season, season_type=season_type))
                if player.player_name == "Stephen Curry":
                    bands.append(distance_band_table(frame, season=season, season_type=season_type))
    if not summary:
        raise RuntimeError("No career caches available. Run without --offline first.")
    summary_df = add_season_peer_percentiles(pd.DataFrame(summary))
    bands_df = pd.concat(bands, ignore_index=True) if bands else pd.DataFrame()
    return summary_df, bands_df


def style_ax(ax):
    ax.spines[["top", "right"]].set_visible(False); ax.grid(axis="y", alpha=.18)


def make_figures(summary: pd.DataFrame, bands: pd.DataFrame) -> dict:
    curry = summary[(summary.player_name == "Stephen Curry") & (summary.season_type == "Regular Season")].sort_values("season_start")
    peer = summary[summary.season_type == "Regular Season"]
    FIGURES.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    axes[0].plot(curry.season, curry.three_rate * 100, marker="o", color="#f5b642", lw=2.7, label="3PT share")
    axes[0].plot(curry.season, curry.deep_rate * 100, marker="o", color="#45a3ff", lw=2.2, label="28+ ft share")
    axes[0].plot(curry.season, curry.very_deep_rate * 100, marker="o", color="#9575ff", lw=2.2, label="30+ ft share")
    axes[0].set_ylabel("Share of all FGA (%)"); axes[0].legend(ncol=3, frameon=False); style_ax(axes[0])
    axes[1].plot(curry.season, curry.deep_attempts_per_game, marker="o", color="#45a3ff", lw=2.7)
    axes[1].set_ylabel("28+ ft attempts / game"); style_ax(axes[1])
    axes[1].tick_params(axis="x", rotation=45); fig.suptitle("How Curry's Effective Shooting Range Evolved", fontsize=18, weight="bold")
    fig.tight_layout(); fig.savefig(FIGURES / "01_career_range_evolution.png", dpi=220); plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 5.5))
    for name, group in peer.groupby("player_name"):
        group = group.sort_values("season_start")
        ax.plot(group.season_start, group.deep_rate * 100, color="#f5b642" if name == "Stephen Curry" else "#718096",
                alpha=1 if name == "Stephen Curry" else .38, lw=3 if name == "Stephen Curry" else 1.2,
                label=name if name == "Stephen Curry" else None)
    ax.set_xlabel("Season start year"); ax.set_ylabel("28+ ft attempts / all FGA (%)"); style_ax(ax); ax.legend(frameon=False)
    ax.set_title("Curry vs Documented Lead-Guard Cohort", loc="left", fontsize=17, weight="bold")
    fig.tight_layout(); fig.savefig(FIGURES / "02_peer_career_comparison.png", dpi=220); plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.plot(curry.season, curry.deep_fg_pct * 100, marker="o", color="#f5b642", lw=2.5)
    ax.fill_between(np.arange(len(curry)), curry.deep_fg_ci_low * 100, curry.deep_fg_ci_high * 100, color="#f5b642", alpha=.2)
    ax.set_ylabel("28+ ft FG% (Wilson 95% interval)"); ax.tick_params(axis="x", rotation=45); style_ax(ax)
    ax.set_title("Deep Accuracy Is Noisy — Show the Uncertainty", loc="left", fontsize=17, weight="bold")
    fig.tight_layout(); fig.savefig(FIGURES / "03_deep_accuracy_uncertainty.png", dpi=220); plt.close(fig)

    playoffs = summary[(summary.player_name == "Stephen Curry") & (summary.season_type == "Playoffs")]
    joined = curry[["season", "deep_rate", "three_rate"]].merge(playoffs[["season", "deep_rate", "three_rate"]], on="season", suffixes=("_regular", "_playoffs"))
    fig, ax = plt.subplots(figsize=(10, 6)); ax.scatter(joined.deep_rate_regular * 100, joined.deep_rate_playoffs * 100, s=65, color="#f5b642")
    if len(joined):
        lim = [0, max(joined[["deep_rate_regular", "deep_rate_playoffs"]].max()) * 110]
        ax.plot(lim, lim, ls="--", color="#718096");
        for row in joined.itertuples(): ax.annotate(row.season, (row.deep_rate_regular * 100, row.deep_rate_playoffs * 100), fontsize=8)
    ax.set_xlabel("Regular season 28+ ft share (%)"); ax.set_ylabel("Playoffs 28+ ft share (%)"); style_ax(ax)
    ax.set_title("Does Curry Preserve Deep Range in the Playoffs?", loc="left", fontsize=17, weight="bold")
    fig.tight_layout(); fig.savefig(FIGURES / "04_regular_vs_playoffs.png", dpi=220); plt.close(fig)
    return {"curry": curry, "joined": joined}


def write_site(summary: pd.DataFrame, bands: pd.DataFrame, derived: dict) -> None:
    curry = derived["curry"]
    peak = curry.loc[curry.deep_attempts_per_game.idxmax()]
    shift = detect_mean_shift(curry.deep_rate)
    shift_season = curry.iloc[int(shift["split_index"])].season if shift else "insufficient data"
    first, latest = curry.iloc[0], curry.iloc[-1]
    annotations = pd.read_csv(ANNOTATIONS)
    rows = "".join(f"<tr><td>{html.escape(r.season)}</td><td>{r.three_rate:.1%}</td><td>{r.deep_rate:.1%}</td><td>{r.very_deep_rate:.1%}</td><td>{r.deep_fg_pct:.1%}</td><td>{r.range_pressure_peer_pctile:.0f}</td><td>{int(r.peer_n)}</td></tr>" for r in curry.itertuples())
    notes = "".join(f"<article><b>{r.season} · {html.escape(r.title)}</b><span>{html.escape(r.note)}</span></article>" for r in annotations.itertuples())
    html_text = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Curry Player Intelligence</title>
<style>:root{{--ink:#eef2f7;--muted:#9aabc0;--bg:#071019;--panel:#101c28;--gold:#f5b642;--blue:#45a3ff}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,Arial,sans-serif}}header,main{{max-width:1240px;margin:auto}}header{{padding:76px 28px 42px}}.eyebrow{{color:var(--gold);font-weight:800;letter-spacing:.12em}}h1{{font-size:clamp(42px,7vw,82px);line-height:.96;margin:16px 0;max-width:1050px}}header p{{font-size:21px;color:var(--muted);max-width:900px;line-height:1.55}}main{{padding:0 28px 90px}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}.card,section{{background:var(--panel);border:1px solid #203144;border-radius:18px}}.card{{padding:22px}}.card b{{display:block;font-size:30px;color:var(--gold)}}.card span,p,li{{color:var(--muted);line-height:1.65}}section{{padding:32px;margin-top:22px}}h2{{font-size:30px;margin:0 0 10px}}img{{width:100%;border-radius:12px;margin-top:20px;background:white}}.two{{display:grid;grid-template-columns:1fr 1fr;gap:22px}}table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{padding:11px;border-bottom:1px solid #29394a;text-align:right}}th:first-child,td:first-child{{text-align:left}}.scroll{{overflow-x:auto}}article{{padding:14px 0;border-bottom:1px solid #29394a}}article span{{display:block;color:var(--muted);margin-top:5px}}.boundary{{border-left:5px solid var(--gold)}}footer{{color:var(--muted);padding-top:30px}}@media(max-width:800px){{.metrics,.two{{grid-template-columns:1fr}}}}</style></head><body>
<header><div class="eyebrow">PLAYER INTELLIGENCE · CAREER STUDY</div><h1>How Stephen Curry Expanded Effective Offensive Space</h1><p>A career-long, uncertainty-aware study of how deep shooting emerged, peaked and changed—benchmarked against a documented lead-guard cohort and separated by regular season and playoffs.</p></header><main>
<div class="metrics"><div class="card"><b>{first.deep_rate:.1%} → {latest.deep_rate:.1%}</b><span>28+ ft attempt share, first to latest season</span></div><div class="card"><b>{peak.season}</b><span>peak deep-attempt volume: {peak.deep_attempts_per_game:.2f}/game</span></div><div class="card"><b>{shift_season}</b><span>descriptive mean-shift candidate</span></div><div class="card"><b>{latest.range_pressure_peer_pctile:.0f}th</b><span>latest documented-cohort percentile (n={int(latest.peer_n)})</span></div></div>
<section><h2>1 · Range evolution</h2><p>The unit of analysis is the player-season. Attempt shares show shot selection; per-game rates separate volume from season length. The detected change point is descriptive—not proof that one event caused the shift.</p><img src="../../figures/curry/career/01_career_range_evolution.png"></section>
<section><h2>2 · Multiple-player comparison</h2><p>Each line uses identical public shot-location definitions. Peers enter only in seasons with available shots; this is a documented guard cohort, not the entire NBA.</p><img src="../../figures/curry/career/02_peer_career_comparison.png"></section>
<div class="two"><section><h2>3 · Accuracy + uncertainty</h2><p>Deep-shot percentages can swing on small samples. Wilson 95% intervals prevent false precision.</p><img src="../../figures/curry/career/03_deep_accuracy_uncertainty.png"></section><section><h2>4 · Playoff translation</h2><p>Matched seasons compare shot selection under a different opponent and game-pressure environment.</p><img src="../../figures/curry/career/04_regular_vs_playoffs.png"></section></div>
<section><h2>5 · Season evidence table</h2><div class="scroll"><table><thead><tr><th>Season</th><th>3PT share</th><th>28+ share</th><th>30+ share</th><th>28+ FG%</th><th>Peer pctile</th><th>Peer n</th></tr></thead><tbody>{rows}</tbody></table></div></section>
<section><h2>6 · Context timeline</h2><p>Annotations are context for interpretation, not causal labels.</p>{notes}</section>
<section class="boundary"><h2>Claim boundary</h2><p><b>This measures effective shooting range—not defensive gravity.</b> NBA public shot charts do not locate defenders, quantify off-ball attention, or identify teammate openness. Percentiles refer only to the named cohort. A causal claim that Curry “changed the league” requires a league-wide diffusion design and rule/era controls; this site establishes the player-level longitudinal evidence.</p></section>
<footer>Data: NBA Stats via nba_api · Generated from cached shot-level records · Methods and processed tables are included in the repository.</footer></main></body></html>'''
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "showcase_template.html").write_text(html_text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--last-season-start", type=int, default=2024); parser.add_argument("--offline", action="store_true"); args = parser.parse_args()
    for path in (RAW, PROCESSED, FIGURES, REPORTS): path.mkdir(parents=True, exist_ok=True)
    summary, bands = build_data(args.last_season_start, args.offline)
    summary.to_csv(PROCESSED / "career_player_season_profiles.csv", index=False)
    bands.to_csv(PROCESSED / "curry_career_distance_bands.csv", index=False)
    derived = make_figures(summary, bands); write_site(summary, bands, derived)
    print(f"Built {len(summary)} player-seasons; Curry regular seasons: {len(derived['curry'])}")

if __name__ == "__main__": main()
