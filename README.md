# Basketball Range Intelligence

An interactive NBA shot-location platform for exploring how player range and
efficiency evolve across seasons.

## What it does

- compares any two qualified NBA players on one coordinate system;
- covers 2009–10 through 2024–25;
- includes 902 players and 4,126 qualified player-seasons;
- labels each player with the team or teams represented in that season;
- replays individual shot attempts in chronological order;
- distinguishes made and missed shots at event level;
- switches between raw shots, attempt density, and cell field-goal percentage;
- tracks 3PT rate, 28+ foot rate, 30+ foot rate, deep accuracy, and average distance;
- uses lazy-loaded player files to keep the browser responsive.

## Product walkthrough

1. Select a season and two players.
2. Use **Career trajectory** to compare long-term shooting profiles.
3. Press **Play shots** to reveal attempts through the selected season.
4. Drag the timeline to inspect a particular point in the season.
5. Switch to **Density** or **FG%** for aggregated spatial comparisons.

Gold filled dots represent made shots. Blue rings represent missed shots. Player
seasons require at least 300 field-goal attempts. Accuracy cells require at least
three attempts. Player selectors are season-aware: only players with eligible data
in the selected season appear, preventing empty comparisons.

## Stack

- React and Vite
- Canvas-based shot maps
- Apache ECharts
- Python, pandas, and NumPy data pipeline
- Pytest regression tests
- Vercel-ready static deployment

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
PYTHONPATH=src python scripts/export_web_data.py

cd web
npm install
npm run dev
```

Open `http://127.0.0.1:5173/`.

## Test and build

```bash
PYTHONPATH=src pytest -q
cd web
npm ci
npm run build
```

The production website is generated in `web/dist/`. The root-level `vercel.json`
allows direct repository import in Vercel. See [DEPLOYMENT.md](DEPLOYMENT.md).

## Data notes

The platform uses NBA Stats shot-location records and a common half-court coordinate
system. Extreme-range metrics use calculated distance from the rim. The public
interface is an exploratory comparison tool; it does not include defender-tracking
or claim to measure defensive gravity.

Before redistributing derived shot records, review the original source terms. Code,
schemas, inclusion rules, and download instructions should remain reproducible even
when third-party raw data cannot be redistributed.
