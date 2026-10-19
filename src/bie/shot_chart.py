from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from .court import draw_nba_half_court

def plot_shot_chart(shots, title='Shot Chart', save_path=None):
    fig, ax = plt.subplots(figsize=(8, 7)); draw_nba_half_court(ax)
    made = shots[shots['SHOT_MADE_FLAG'] == 1]; missed = shots[shots['SHOT_MADE_FLAG'] == 0]
    ax.scatter(missed['LOC_X'], missed['LOC_Y'], marker='x', alpha=0.45, label='Missed', s=22)
    ax.scatter(made['LOC_X'], made['LOC_Y'], marker='o', alpha=0.55, label='Made', s=22)
    ax.set_title(title, fontsize=15, pad=14); ax.legend(loc='upper right', frameon=False)
    if save_path:
        save_path=Path(save_path); save_path.parent.mkdir(parents=True, exist_ok=True); fig.savefig(save_path, dpi=200, bbox_inches='tight')
    return fig, ax

def plot_shot_density(shots, title='Shot Density Map', save_path=None):
    fig, ax = plt.subplots(figsize=(8, 7)); draw_nba_half_court(ax)
    ax.hexbin(shots['LOC_X'], shots['LOC_Y'], gridsize=30, mincnt=1, alpha=0.75)
    ax.set_title(title, fontsize=15, pad=14)
    if save_path:
        save_path=Path(save_path); save_path.parent.mkdir(parents=True, exist_ok=True); fig.savefig(save_path, dpi=200, bbox_inches='tight')
    return fig, ax

def summarize_shots(shots):
    zone_cols = ['SHOT_ZONE_BASIC','SHOT_ZONE_AREA','SHOT_ZONE_RANGE']
    available = [c for c in zone_cols if c in shots.columns]
    grouped = shots.groupby(available).agg(attempts=('SHOT_MADE_FLAG','size'), makes=('SHOT_MADE_FLAG','sum'), fg_pct=('SHOT_MADE_FLAG','mean')).reset_index()
    if 'SHOT_TYPE' in shots.columns:
        temp = shots.copy(); temp['point_value'] = temp['SHOT_TYPE'].astype(str).str.contains('3PT').map({True:3, False:2}); temp['points']=temp['SHOT_MADE_FLAG']*temp['point_value']
        ep = temp.groupby(available)['points'].mean().reset_index(name='expected_points')
        grouped = grouped.merge(ep, on=available, how='left')
    return grouped.sort_values('attempts', ascending=False)
