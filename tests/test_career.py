import pandas as pd

from bie.career import add_season_peer_percentiles, detect_mean_shift, summarize_player_season


def shots(distances, made=None):
    made = made or [1] * len(distances)
    return pd.DataFrame({
        "LOC_X": [d * 10 for d in distances], "LOC_Y": [0] * len(distances),
        "SHOT_MADE_FLAG": made,
        "SHOT_TYPE": ["3PT Field Goal" if d >= 24 else "2PT Field Goal" for d in distances],
        "GAME_ID": [1, 1, 2, 2][:len(distances)],
    })


def test_season_summary_normalizes_by_games_and_has_wilson_interval():
    row = summarize_player_season(shots([3, 25, 28, 31], [1, 1, 0, 1]),
                                  player_name="A", season="2024-25", season_type="Regular Season")
    assert row["fga_per_game"] == 2
    assert row["deep_attempts"] == 2
    assert row["deep_fg_ci_low"] < row["deep_fg_pct"] < row["deep_fg_ci_high"]


def test_peer_percentiles_are_season_specific():
    frame = pd.DataFrame({
        "player_name": ["A", "B"], "season": ["2024-25"] * 2,
        "season_type": ["Regular Season"] * 2,
        "three_rate": [.8, .4], "deep_rate": [.4, .1], "very_deep_rate": [.2, .01],
        "avg_shot_distance_ft": [23, 15],
    })
    out = add_season_peer_percentiles(frame)
    assert out.loc[0, "range_pressure_peer_pctile"] == 100
    assert out.loc[0, "peer_n"] == 2


def test_change_point_detects_large_shift():
    result = detect_mean_shift(pd.Series([1, 1, 1, 5, 5, 5]))
    assert result["split_index"] == 3
