import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Arc

def draw_nba_half_court(ax=None, linewidth=1.5):
    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 6))
    patches = [
        Circle((0, 0), radius=7.5, fill=False, linewidth=linewidth),
        Rectangle((-30, -7.5), 60, -1, linewidth=linewidth, fill=False),
        Rectangle((-80, -47.5), 160, 190, linewidth=linewidth, fill=False),
        Rectangle((-60, -47.5), 120, 190, linewidth=linewidth, fill=False),
        Arc((0, 142.5), 120, 120, theta1=0, theta2=180, linewidth=linewidth),
        Arc((0, 142.5), 120, 120, theta1=180, theta2=360, linewidth=linewidth, linestyle='dashed'),
        Arc((0, 0), 80, 80, theta1=0, theta2=180, linewidth=linewidth),
        Rectangle((-220, -47.5), 0, 140, linewidth=linewidth, fill=False),
        Rectangle((220, -47.5), 0, 140, linewidth=linewidth, fill=False),
        Arc((0, 0), 475, 475, theta1=22, theta2=158, linewidth=linewidth),
        Arc((0, 422.5), 120, 120, theta1=180, theta2=360, linewidth=linewidth),
    ]
    for p in patches: ax.add_patch(p)
    ax.set_xlim(-250, 250); ax.set_ylim(-50, 470); ax.set_aspect('equal'); ax.axis('off')
    return ax
