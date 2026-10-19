#!/usr/bin/env python3
"""Build a self-contained interactive career and league shooting platform."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly

from bie.career import season_label_start
from bie.data_loader import load_local_shots, load_nba_api_shots, save_processed
from bie.range_pressure import add_range_features

ROOT = Path(__file__).resolve().parents[1]
CAREER = ROOT / "data/raw/career"
LEAGUE = ROOT / "data/raw/league"
PROCESSED = ROOT / "data/processed"
OUTPUT = ROOT / "reports/curry/showcase_template.html"


def seasons(last_start: int):
    return [f"{y}-{str(y + 1)[-2:]}" for y in range(2009, last_start + 1)]


def load_or_download_league(season: str, offline: bool) -> pd.DataFrame | None:
    path = LEAGUE / f"{season}_regular_complete.csv"
    if path.exists(): return load_local_shots(path)
    if offline: return None
    start = season_label_start(season); frames = []
    # The unfiltered endpoint silently caps results near 100k rows. Calendar chunks
    # remain below that cap and also cover the 2019-20 bubble.
    ranges = [(f"10/01/{start}", f"12/31/{start}"),
              (f"01/01/{start+1}", f"03/31/{start+1}"),
              (f"04/01/{start+1}", f"06/30/{start+1}"),
              (f"07/01/{start+1}", f"10/31/{start+1}")]
    for date_from, date_to in ranges:
        try:
            frames.append(load_nba_api_shots(0, season, season_type="Regular Season",
                                              date_from=date_from, date_to=date_to, retries=2))
        except RuntimeError as exc:
            if "contains no attempts" not in str(exc):
                print(f"SKIP league chunk {season} {date_from}: {exc}"); return None
    if not frames: return None
    frame = pd.concat(frames, ignore_index=True).drop_duplicates(["GAME_ID", "GAME_EVENT_ID"])
    if len(frame) < 120_000 and season != "2011-12":
        raise RuntimeError(f"League season {season} failed completeness check: {len(frame)} FGA")
    save_processed(frame, path); return frame


def league_summary(last_start: int, offline: bool) -> pd.DataFrame:
    rows = []
    for season in seasons(last_start):
        print(f"League {season}")
        raw = load_or_download_league(season, offline)
        if raw is None: continue
        df = add_range_features(raw)
        players = (df.groupby(["PLAYER_ID", "PLAYER_NAME"])
                   .agg(fga=("SHOT_MADE_FLAG", "size"), three_rate=("is_three", "mean"),
                        deep_rate=("is_deep_three", "mean"), very_deep_rate=("is_very_deep", "mean"),
                        avg_distance=("distance_from_rim_ft", "mean")).reset_index())
        eligible = players[players.fga >= 300]
        rows.append({
            "season": season, "season_start": season_label_start(season), "league_fga": len(df),
            "league_three_rate": df.is_three.mean(), "league_deep_rate": df.is_deep_three.mean(),
            "league_very_deep_rate": df.is_very_deep.mean(), "eligible_players": len(eligible),
            "eligible_median_deep_rate": eligible.deep_rate.median(),
            "eligible_p90_deep_rate": eligible.deep_rate.quantile(.9),
            "eligible_p95_deep_rate": eligible.deep_rate.quantile(.95),
        })
    out = pd.DataFrame(rows); out.to_csv(PROCESSED / "league_range_diffusion.csv", index=False); return out


def shot_grid_payload() -> dict:
    payload = {}
    for path in CAREER.rglob("*_regular.csv"):
        player = path.parent.name.replace("_", " ").title().replace("Doncic", "Doncic")
        season = path.stem.replace("_regular", "")
        df = load_local_shots(path)
        # Counts and makes on a common 10x10 inch court grid; compact enough to embed.
        x_edges = np.linspace(-250, 250, 31); y_edges = np.linspace(-50, 420, 31)
        attempts, _, _ = np.histogram2d(df.LOC_X, df.LOC_Y, bins=[x_edges, y_edges])
        made, _, _ = np.histogram2d(df.loc[df.SHOT_MADE_FLAG == 1, "LOC_X"],
                                    df.loc[df.SHOT_MADE_FLAG == 1, "LOC_Y"], bins=[x_edges, y_edges])
        payload[f"{player}|{season}"] = {"attempts": attempts.T.astype(int).tolist(),
                                          "made": made.T.astype(int).tolist()}
    return payload


def json_records(df):
    return json.loads(df.replace({np.nan: None}).to_json(orient="records"))


def build_html(career: pd.DataFrame, league: pd.DataFrame, grids: dict):
    plotly_js = plotly.offline.get_plotlyjs()
    data = json.dumps({"career": json_records(career), "league": json_records(league), "grids": grids}, separators=(",", ":"))
    template = (ROOT / "templates/interactive_platform.html").read_text(encoding="utf-8")
    OUTPUT.write_text(template.replace("/*__PLOTLY__*/", plotly_js).replace("/*__DATA__*/", data), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(); p.add_argument("--last-season-start", type=int, default=2024); p.add_argument("--offline", action="store_true"); a = p.parse_args()
    LEAGUE.mkdir(parents=True, exist_ok=True); PROCESSED.mkdir(parents=True, exist_ok=True); OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    career = pd.read_csv(PROCESSED / "career_player_season_profiles.csv")
    league = league_summary(a.last_season_start, a.offline)
    build_html(career, league, shot_grid_payload())
    print(f"Platform: {OUTPUT} | league seasons={len(league)} | grids={len(shot_grid_payload())}")

if __name__ == "__main__": main()
