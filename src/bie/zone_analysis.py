import pandas as pd
import numpy as np

def add_distance_features(shots):
    df = shots.copy(); df['distance_from_rim'] = np.sqrt(df['LOC_X']**2 + df['LOC_Y']**2)/10; df['shot_angle'] = np.degrees(np.arctan2(df['LOC_Y'], df['LOC_X'])); return df

def classify_curry_range(shots):
    df = add_distance_features(shots)
    bins=[0,4,8,16,23.75,28,35,100]
    labels=['rim','paint_non_rim','midrange','regular_three','deep_three','logo_range','extreme_range']
    df['curry_range_zone'] = pd.cut(df['distance_from_rim'], bins=bins, labels=labels, right=False)
    return df

def range_summary(shots):
    df = classify_curry_range(shots)
    return df.groupby('curry_range_zone', observed=True).agg(attempts=('SHOT_MADE_FLAG','size'), makes=('SHOT_MADE_FLAG','sum'), fg_pct=('SHOT_MADE_FLAG','mean'), avg_distance=('distance_from_rim','mean')).reset_index()
