import numpy as np
import pandas as pd
import pytest

from bie.data_loader import validate_shot_columns
from bie.range_pressure import (
    add_peer_percentiles,
    bootstrap_range_profile,
    build_peer_benchmark,
    summarize_range_profile,
)


def shots(distances, made, three=None):
    distances = np.asarray(distances, dtype=float)
    if three is None:
        three = distances >= 23.75
    return pd.DataFrame(
        {
            "LOC_X": distances * 10,
            "LOC_Y": np.zeros(len(distances)),
            "SHOT_MADE_FLAG": made,
            "SHOT_TYPE": np.where(three, "3PT Field Goal", "2PT Field Goal"),
        }
    )


def test_validation_rejects_missing_columns():
    with pytest.raises(ValueError, match="missing required"):
        validate_shot_columns(pd.DataFrame({"LOC_X": [0]}))


def test_profile_uses_feet_and_shrinks_sparse_deep_accuracy():
    df = shots([2, 24, 28, 30], [1, 1, 1, 0])
    result = summarize_range_profile(df, player_name="Test")
    assert result["attempts"] == 4
    assert result["deep_three_attempts"] == 2
    assert result["deep_three_rate"] == pytest.approx(0.5)
    assert result["avg_shot_distance_ft"] == pytest.approx(21.0)
    assert 0.35 < result["deep_three_eb_fg_pct"] < 0.5


def test_benchmark_and_percentiles_rank_longer_profile_higher():
    cohort = {
        "Short": shots([2, 8, 15, 24], [1, 1, 0, 1]),
        "Medium": shots([5, 20, 25, 28], [1, 0, 1, 0]),
        "Long": shots([24, 28, 30, 33], [1, 1, 1, 0]),
    }
    ranked = add_peer_percentiles(build_peer_benchmark(cohort))
    assert ranked.iloc[0]["player_name"] == "Long"
    assert ranked["range_pressure_index"].between(0, 100).all()


def test_bootstrap_is_reproducible_and_contains_point_estimate():
    df = shots([2, 10, 24, 28, 30, 31] * 10, [1, 1, 0, 1, 0, 1] * 10)
    result = bootstrap_range_profile(df, n_boot=100, seed=7)
    assert set(result.columns) == {"metric", "estimate", "ci_low", "ci_high", "confidence"}
    assert (result["ci_low"] <= result["estimate"]).all()
    assert (result["estimate"] <= result["ci_high"]).all()
