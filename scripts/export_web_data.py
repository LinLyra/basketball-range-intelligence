#!/usr/bin/env python3
"""Export compact, season-split JSON for the React intelligence platform."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from bie.range_pressure import add_range_features

ROOT=Path(__file__).resolve().parents[1]; LEAGUE=ROOT/'data/raw/league'; OUT=ROOT/'web/public/data'
OUT.mkdir(parents=True,exist_ok=True)
SHOTS=OUT/'shots'

def clean(v):
    if isinstance(v,(np.integer,)): return int(v)
    if isinstance(v,(float,np.floating)): return None if pd.isna(v) else round(float(v),6)
    return v

def main():
    index=[]; career=[]
    for path in sorted(LEAGUE.glob('*_regular_complete.csv')):
        season=path.name[:7]; print(season)
        raw=pd.read_csv(path); df=add_range_features(raw)
        df['player_id']=df.PLAYER_ID.astype(int); df['player_name']=df.PLAYER_NAME.astype(str)
        # Fine 10-inch cells preserve spatial structure without the blocky 20-inch bins.
        summaries=[]; grids={}; xedges=np.linspace(-250,250,51); yedges=np.linspace(-50,425,49)
        season_shots=SHOTS/season; season_shots.mkdir(parents=True,exist_ok=True)
        for (pid,name),g in df.groupby(['player_id','player_name']):
            if len(g)<300: continue
            games=g.GAME_ID.nunique(); deep=g[g.is_deep_three]; very=g[g.is_very_deep]; threes=g[g.is_three]
            row={'player_id':int(pid),'player_name':name,'fga':len(g),'games':int(games),
                 'fga_per_game':len(g)/games,'three_rate':g.is_three.mean(),'three_fg_pct':threes.SHOT_MADE_FLAG.mean(),
                 'deep_rate':g.is_deep_three.mean(),'deep_fg_pct':deep.SHOT_MADE_FLAG.mean() if len(deep) else None,
                 'very_deep_rate':g.is_very_deep.mean(),'avg_distance':g.distance_from_rim_ft.mean()}
            summaries.append({k:clean(v) for k,v in row.items()})
            att,_,_=np.histogram2d(g.LOC_X,g.LOC_Y,bins=[xedges,yedges]); mg=g[g.SHOT_MADE_FLAG==1]
            made,_,_=np.histogram2d(mg.LOC_X,mg.LOC_Y,bins=[xedges,yedges])
            grids[str(pid)]={'a':att.T.astype(int).tolist(),'m':made.T.astype(int).tolist()}
            order=[c for c in ['GAME_DATE','GAME_ID','GAME_EVENT_ID'] if c in g.columns]
            events=g.sort_values(order) if order else g
            compact=[[clean(r.LOC_X),clean(r.LOC_Y),int(r.SHOT_MADE_FLAG),str(r.GAME_DATE)[:10]]
                     for r in events.itertuples()]
            (season_shots/f'{pid}.json').write_text(
                json.dumps(compact,separators=(',',':')),encoding='utf-8')
        summaries.sort(key=lambda r:r['player_name'])
        payload={'season':season,'players':summaries,'grids':grids}
        (OUT/f'{season}.json').write_text(json.dumps(payload,separators=(',',':')),encoding='utf-8')
        index.append({'season':season,'players':[{'id':r['player_id'],'name':r['player_name']} for r in summaries]})
        career.extend([{'season':season,**r} for r in summaries])
    (OUT/'index.json').write_text(json.dumps({'seasons':index},separators=(',',':')),encoding='utf-8')
    (OUT/'career.json').write_text(json.dumps(career,separators=(',',':')),encoding='utf-8')
    print(f'exported {len(index)} seasons, {sum(len(x["players"]) for x in index)} eligible player-seasons')
if __name__=='__main__': main()
