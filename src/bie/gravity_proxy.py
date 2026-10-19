import warnings

import pandas as pd

from .range_pressure import summarize_range_profile

def calculate_shooting_gravity_proxy(shots):
    warnings.warn(
        "calculate_shooting_gravity_proxy is deprecated: shot locations do not "
        "measure defensive gravity. Use summarize_range_profile instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return pd.DataFrame([summarize_range_profile(shots, player_name="Stephen Curry")])

def explain_gravity_proxy():
    return (
        "Public shot locations describe range pressure, not defensive gravity. "
        "True gravity requires defender/player tracking or a validated causal proxy."
    )
