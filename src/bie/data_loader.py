from pathlib import Path
import time

import pandas as pd


REQUIRED_SHOT_COLUMNS = {
    "LOC_X",
    "LOC_Y",
    "SHOT_MADE_FLAG",
    "SHOT_TYPE",
}

def load_local_shots(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f'Could not find file: {path}')
    shots = pd.read_csv(path)
    validate_shot_columns(shots)
    return shots

def save_processed(df, path):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True); df.to_csv(path, index=False)

def validate_shot_columns(shots: pd.DataFrame) -> None:
    """Fail early when a cached/API response is not a usable shot table."""
    missing = REQUIRED_SHOT_COLUMNS.difference(shots.columns)
    if missing:
        raise ValueError(f"Shot data is missing required columns: {sorted(missing)}")
    if shots.empty:
        raise ValueError("Shot data contains no attempts")
    if not shots["SHOT_MADE_FLAG"].dropna().isin([0, 1]).all():
        raise ValueError("SHOT_MADE_FLAG must contain only 0/1 values")


def load_nba_api_shots(
    player_id: int,
    season: str = "2024-25",
    *,
    season_type: str = "Regular Season",
    date_from: str = "",
    date_to: str = "",
    retries: int = 3,
    pause_seconds: float = 1.5,
):
    """Download one regular-season shot chart with bounded retries.

    NBA Stats is an operational dependency rather than a stable research archive.
    Callers should immediately cache the returned table and record the retrieval date.
    """
    from nba_api.stats.endpoints import shotchartdetail

    last_error = None
    for attempt in range(retries):
        try:
            response = shotchartdetail.ShotChartDetail(
                team_id=0,
                player_id=player_id,
                season_nullable=season,
                context_measure_simple="FGA",
                season_type_all_star=season_type,
                date_from_nullable=date_from,
                date_to_nullable=date_to,
                timeout=60,
            )
            shots = response.get_data_frames()[0]
            validate_shot_columns(shots)
            return shots
        except Exception as exc:  # pragma: no cover - network behavior
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(pause_seconds * (attempt + 1))
    raise RuntimeError(
        f"NBA Stats download failed after {retries} attempts for player {player_id}, "
        f"season {season}: {last_error}"
    ) from last_error
