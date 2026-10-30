"""Paired test of AUC(post) - AUC(pre) on the test split, for each feature set.

Same users on both sides, so pairs are resampled once per draw and the difference is taken within the draw.
Refits the saved models from train.csv with the C chosen by train.py.
  user:          user probabilities averaged within a period
  user_equal:    as user, with each user's periods cut to the same number of random intervals
  interval:      one score per interval
Models: 'all' is one model trained on both periods; 'own_period' scores pre and post with models
trained on that period only.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata
from statsmodels.stats.multitest import multipletests

from train import OUT, RESULTS, SEED, feature_sets, model

N_DRAWS = 10_000
rng = np.random.default_rng(SEED)


def auc(y, p):
    """Mann-Whitney AUC; quick enough to run inside the resampling loops."""
    positives = y.sum()
    negatives = len(y) - positives
    return (rankdata(p)[y == 1].sum() - positives * (positives + 1) / 2) / (positives * negatives)


def user_table(frame, equal):
    """One row per user and period, as arrays pair x condition x period."""
    rows = frame
    if equal:
        rank = frame.assign(key=rng.random(len(frame))).groupby(['pair_id', 'condition', 'period'])['key'].rank()
        limit = frame.groupby(['pair_id', 'condition', 'period'])['p'].transform('size')
        limit = limit.groupby([frame['pair_id'], frame['condition']]).transform('min')
        rows = frame[rank <= limit]
    return rows.groupby(['pair_id', 'label', 'period'])['p'].mean().unstack(['label', 'period'])


def user_difference(table, pairs):
    """table columns: (label, period). Stacks depression and control scores for the chosen pairs."""
    y = np.r_[np.ones(len(pairs)), np.zeros(len(pairs))]
    values = {period: np.r_[table[(1, period)].to_numpy()[pairs], table[(0, period)].to_numpy()[pairs]]
              for period in ['pre', 'post']}
    return auc(y, values['post']) - auc(y, values['pre']), values, y


def interval_difference(frames, pairs):
    """frames: pair -> (labels, p, is_post)."""
    y, p, post = (np.concatenate([frames[i][k] for i in pairs]) for k in range(3))
    return auc(y[post], p[post]) - auc(y[~post], p[~post])


def summarize(observed, draws, null):
    return {'auc_difference': observed, 'ci_low': np.quantile(draws, 0.025), 'ci_high': np.quantile(draws, 0.975),
            'p_bootstrap': min(1, 2 * min((draws <= 0).mean(), (draws >= 0).mean())),
            'p_permutation': (1 + (np.abs(null) >= abs(observed)).sum()) / (1 + len(null))}


def test_user(frame, equal):
    n = frame['pair_id'].nunique()
    table = user_table(frame, equal)
    # an equal-interval score depends on the subsample drawn, so it is averaged over many of them
    observed = np.mean([user_difference(user_table(frame, True), np.arange(n))[0] for _ in range(200)]) if equal \
        else user_difference(table, np.arange(n))[0]
    draws, null = np.empty(N_DRAWS), np.empty(N_DRAWS)
    for i in range(N_DRAWS):
        if equal and i % 100 == 0:      # fresh interval subsample every 100 draws
            table = user_table(frame, True)
        draws[i] = user_difference(table, rng.integers(n, size=n))[0]

    y = np.r_[np.ones(n), np.zeros(n)]
    for i in range(N_DRAWS):
        if i == 0 or (equal and i % 100 == 0):
            table = user_table(frame, equal)
            pre = np.c_[table[(1, 'pre')], table[(0, 'pre')]]
            post = np.c_[table[(1, 'post')], table[(0, 'post')]]
        swap = rng.random(n) < 0.5      # a pair's two periods are exchangeable if period does not matter
        a, b = np.where(swap[:, None], pre, post), np.where(swap[:, None], post, pre)
        null[i] = auc(y, a.T.ravel()) - auc(y, b.T.ravel())
    return summarize(observed, draws, null)


def test_interval(frame):
    frames = [(g['label'].to_numpy(), g['p'].to_numpy(), g['period'].eq('post').to_numpy()) for _, g in frame.groupby('pair_id')]
    n = len(frames)
    observed = interval_difference(frames, np.arange(n))
    draws = np.array([interval_difference(frames, rng.integers(n, size=n)) for _ in range(N_DRAWS)])
    null = np.empty(N_DRAWS)
    for i in range(N_DRAWS):
        swapped = [(y, p, ~post if rng.random() < 0.5 else post) for y, p, post in frames]
        null[i] = interval_difference(swapped, np.arange(n))
    return summarize(observed, draws, null)


def predictions(train, test, columns, chosen):
    fit = lambda period: model(chosen[period]).fit(*(lambda d: (d[columns], d['label']))(train if period == 'all' else train[train['period'] == period]))
    both = fit('all').predict_proba(test[columns])[:, 1]
    own = np.where(test['period'] == 'post', fit('post').predict_proba(test[columns])[:, 1], fit('pre').predict_proba(test[columns])[:, 1])
    return {'all': both, 'own_period': own}


def main():
    train, test = pd.read_csv(OUT / 'train.csv'), pd.read_csv(OUT / 'test.csv')
    performance = pd.read_csv(RESULTS / 'performance.csv')
    rows = []
    for name, columns in feature_sets.items():
        chosen = performance[performance['feature_set'] == name].groupby('trained_on')['C'].first().to_dict()
        for trained, p in predictions(train, test, columns, chosen).items():
            frame = test[['pair_id', 'label', 'condition', 'period']].assign(p=p)
            for level, result in {'user': lambda: test_user(frame, False), 'user_equal': lambda: test_user(frame, True),
                                  'interval': lambda: test_interval(frame)}.items():
                rows.append({'feature_set': name, 'model': trained, 'level': level, **result()})
                print(rows[-1], flush=True)
    results = pd.DataFrame(rows)
    results['p_holm'] = results.groupby(['model', 'level'])['p_bootstrap'].transform(lambda p: multipletests(p, method='holm')[1])
    results.to_csv(RESULTS / 'pre_post_test.csv', index=False)
    print(results.round(4).to_string())


if __name__ == '__main__':
    main()
