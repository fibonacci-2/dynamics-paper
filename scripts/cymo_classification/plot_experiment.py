"""One-figure overview of the experiment: how rows are built, scores by period, and the pre vs post test."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

RESULTS = Path('results/cymo_classification')
INK, MUTED, GRID, BOX = '#0b0b0b', '#52514e', '#e6e5e0', '#f4f3ef'
PRE, POST = '#2a78d6', '#eb6834'
ORDER = ['All CYMO', 'Stylistics', 'Syntactic Complexity', 'Lexical Complexity', 'Readability', 'Activity baseline']
STEPS = [('Sentences', 'CYMO scores,\n44 measures'), ('Posts', 'sentences\naveraged'),
         ('30-day intervals', 'posts averaged,\n≥500 words, ≥3 posts'), ('Users', '≥8 intervals, 180+ days,\nboth periods'),
         ('1:1 pairs', '1,055 pairs, split\n744 / 147 / 164'), ('Logistic regression', '6 feature sets,\nscored on pre and post')]

plt.rcParams.update({'font.size': 9, 'axes.titlesize': 10, 'axes.titleweight': 'bold', 'axes.titlelocation': 'left',
                     'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': MUTED,
                     'axes.labelcolor': INK, 'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.grid': True,
                     'grid.color': GRID, 'grid.linewidth': 0.6, 'axes.axisbelow': True})


def pipeline(ax):
    ax.axis('off')
    ax.set(xlim=(0, len(STEPS)), ylim=(0, 1))
    ax.set_title('A. How the data was built', pad=8)
    for i, (name, detail) in enumerate(STEPS):
        ax.add_patch(FancyBboxPatch((i + 0.04, 0.04), 0.8, 0.92, boxstyle='round,pad=0,rounding_size=0.03',
                                    fc=BOX, ec='none', mutation_aspect=4))
        ax.text(i + 0.44, 0.74, name, ha='center', va='center', fontweight='bold', color=INK, fontsize=9)
        ax.text(i + 0.44, 0.34, detail, ha='center', va='center', color=MUTED, fontsize=7.5, linespacing=1.3)
        if i < len(STEPS) - 1:
            ax.add_patch(FancyArrowPatch((i + 0.86, 0.5), (i + 1.02, 0.5), arrowstyle='-|>', mutation_scale=9, color=MUTED, lw=1))


def period_panel(ax, performance, level, title):
    y = np.arange(len(ORDER))
    rows = performance[(performance['trained_on'] == 'all') & (performance['level'] == level)].set_index(['feature_set', 'tested_on'])
    for period, color, offset, label in [('pre', PRE, -0.16, 'Before diagnosis'), ('post', POST, 0.16, 'After diagnosis')]:
        part = rows.xs(period, level='tested_on').loc[ORDER]
        ax.hlines(y + offset, part['auc_low'], part['auc_high'], color=color, lw=2)
        ax.scatter(part['auc'], y + offset, color=color, s=34, zorder=3, edgecolor='white', linewidth=1, label=label)
    ax.set_yticks(y, ORDER)
    ax.set(xlim=(0.6, 0.95), xlabel='Test AUC (95% CI)', title=title)
    ax.grid(axis='y', visible=False)


def test_panel(ax, tests):
    levels = [('interval', 'Per interval'), ('user', 'Per user'), ('user_equal', 'Per user,\nequal intervals')]
    rows = tests[(tests['feature_set'] == 'All CYMO') & (tests['model'] == 'all')].set_index('level')
    ax.axvline(0, color=MUTED, lw=1)
    for y, (level, _) in enumerate(levels):
        row = rows.loc[level]
        ax.hlines(y, row['ci_low'], row['ci_high'], color=INK, lw=2)
        ax.scatter(row['auc_difference'], y, color=INK, s=34, zorder=3, edgecolor='white', linewidth=1)
        ax.text(0.128, y - 0.2, f"{row['auc_difference']:+.3f}, corrected p = {row['p_holm']:.3f}", ha='right', va='bottom', fontsize=8, color=INK)
    ax.set_yticks(range(3), [label for _, label in levels])
    ax.set(xlim=(-0.05, 0.13), ylim=(2.5, -0.6), xlabel='AUC after − before (95% CI)', title='D. Pre vs post test, All CYMO')
    ax.grid(axis='y', visible=False)


performance = pd.read_csv(RESULTS / 'performance.csv')
tests = pd.read_csv(RESULTS / 'pre_post_test.csv')

fig = plt.figure(figsize=(13, 6.6), layout='constrained')
grid = fig.add_gridspec(2, 3, height_ratios=[1, 3.2], width_ratios=[1.1, 1, 1])
pipeline(fig.add_subplot(grid[0, :]))
left = fig.add_subplot(grid[1, 0])
period_panel(left, performance, 'interval', 'B. One month at a time (per interval)')
right = fig.add_subplot(grid[1, 1], sharey=left)
period_panel(right, performance, 'user', "C. All of a user's months (per user)")
right.tick_params(labelleft=False)
left.invert_yaxis()
left.legend(loc='upper left', bbox_to_anchor=(0, -0.13), ncols=2, frameon=False, fontsize=8.5, handletextpad=0.2)
test_panel(fig.add_subplot(grid[1, 2]), tests)
fig.savefig(RESULTS / 'experiment_overview.png', dpi=200, bbox_inches='tight', facecolor='white')
