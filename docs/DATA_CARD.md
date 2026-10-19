# Data Card

## Source

NBA Stats shot-chart endpoint accessed through `nba_api`. The endpoint is public
but operationally unstable and not a versioned research archive.

## Unit of observation

One regular-season field-goal attempt for one selected player-season.

## Cohort

The comparison set is manually documented in `configs/peer_cohort.csv`. It contrasts
Curry with lead guards and high-volume perimeter scorers; it is not random or exhaustive.

## Known limitations

- No defender location, off-ball movement or teammate openness.
- No possession-level role adjustment.
- No opponent, score or clock adjustment in the descriptive index.
- NBA coordinates and event labels must be audited against season totals.
- API values may be corrected or changed after retrieval.

## Intended use

Portfolio-grade descriptive spatial analysis and a baseline for a later defensive
gravity study.

## Prohibited claim

Do not describe the Range Pressure Index as direct measurement of defensive gravity.
