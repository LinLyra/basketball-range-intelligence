# Methodology and Claim Boundary

## Research question

How unusual is Stephen Curry's public shot-range profile relative to a documented
cohort of high-usage lead guards and perimeter scorers?

This version deliberately does not claim to estimate true defensive gravity.
Gravity is a response by defenders and teammates; shot locations contain no direct
observation of that response.

## Inputs

Regular-season NBA Stats shot-chart records with at least `LOC_X`, `LOC_Y`,
`SHOT_MADE_FLAG` and `SHOT_TYPE`. The retrieval script caches each player-season
response because the NBA Stats endpoint is not a versioned archive.

## Range definitions

- Three: NBA API `SHOT_TYPE` contains `3PT`.
- Deep three: distance from rim at least 28 feet.
- Very deep attempt: distance from rim at least 30 feet.
- Distance: `sqrt(LOC_X^2 + LOC_Y^2) / 10` feet.

## Sparse-attempt adjustment

Observed deep-three accuracy is unstable. The reported adjusted value uses a
Beta-Binomial posterior mean equivalent to 35 prior makes in 100 attempts:

`(deep makes + 35) / (deep attempts + 100)`.

This prior is explicit and must receive a sensitivity analysis before academic use.

## Peer-normalized index

Empirical percentile ranks are calculated within the documented cohort for
three-point rate, deep-three rate, 30+ foot rate, average shot distance and
adjusted deep-three accuracy. Their unweighted mean is the Range Pressure Index.
It is not a learned causal quantity and not a league percentile.

## Uncertainty

Attempt-level bootstrap intervals describe sampling variability. They do not
account for within-game dependence, opponent, score, clock, possession role or
selection into attempts. A research version should use game-clustered resampling
and a multilevel shot model.

## Required next step for true gravity

At least one of the following is required: player tracking of defender displacement,
possession-level teammate openness, screen/off-ball-route annotations, or adjusted
on/off models with explicit causal assumptions.
