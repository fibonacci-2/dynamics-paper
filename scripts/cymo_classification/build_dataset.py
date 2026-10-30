"""Compile the depression vs control interval dataset and save its splits as CSV.

Follows cymo.ipynb: sentences -> posts -> 30-day intervals, with the same validity and cohort rules.
Intervals are anchored on each user's diagnosis date so that no interval straddles it. Each depression
user is paired 1:1 with an unused control, who takes that user's date as a pseudo-diagnosis date.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.parquet as pq

DATA = Path('data/cymo')
OUT = Path('data/cymo_classification')
DISCLOSURES = 'data/depression_self_disclosures.jsonl'

INTERVAL_DAYS = 30
MIN_WORDS = 500        # per interval
MIN_POSTS = 3          # per interval
MIN_INTERVALS = 8      # valid intervals per participant
MIN_SPAN_DAYS = 180    # first to last valid interval
SPLITS = {'train': 0.70, 'val': 0.15, 'test': 0.15}
SEED = 42

interval_s = INTERVAL_DAYS * 86400
features = list(json.load(open(DATA / 'float64_features.json'))['features'])


def dated_posts(condition):
    """One row per CYMO post with a timestamp, sorted by user and time."""
    keys = pq.read_table(DATA / f'final_{condition}_cymo_sentences.parquet', columns=['user_id', 'post_id'])
    keys = keys.to_pandas().drop_duplicates()
    keys['user_id'] = keys['user_id'].astype(str)
    meta = pd.read_parquet(OUT / f'metadata_{condition}.parquet', columns=['user_id', 'post_id', 'created_utc', 'word_count'])
    posts = keys.merge(meta, on=['user_id', 'post_id']).dropna(subset=['created_utc'])
    posts['user_id'] = posts['user_id'].astype(int)
    return posts.sort_values(['user_id', 'created_utc'], ignore_index=True)


def interval_counts(t, words, index_utc):
    """Valid anchored intervals for one user: the notebook's rules, with bins counted from index_utc."""
    bins = np.floor((t - index_utc) / interval_s).astype(int)
    values, inverse = np.unique(bins, return_inverse=True)
    n_posts = np.bincount(inverse)
    n_words = np.bincount(inverse, weights=words)
    return values[(n_words >= MIN_WORDS) & (n_posts >= MIN_POSTS)]


def summary(t, words, index_utc):
    """(pre, post) valid-interval counts, or None when the user fails the cohort rules."""
    valid = interval_counts(t, words, index_utc)
    n_pre, n_post = (valid < 0).sum(), (valid >= 0).sum()
    if not n_pre or not n_post or len(valid) < MIN_INTERVALS:
        return None
    if (valid.max() - valid.min()) * INTERVAL_DAYS < MIN_SPAN_DAYS:
        return None
    return n_pre, n_post


def by_user(posts):
    """Per-user timestamp and word arrays, without a Python groupby over millions of rows."""
    users, starts = np.unique(posts['user_id'].to_numpy(), return_index=True)
    ends = np.append(starts[1:], len(posts))
    t, words = posts['created_utc'].to_numpy(), posts['word_count'].to_numpy()
    return {u: (t[a:b], words[a:b]) for u, a, b in zip(users, starts, ends)}


def calendar_valid(posts):
    """users x calendar bins: valid-interval indicator, used to shortlist controls quickly."""
    bins = np.floor(posts['created_utc'].to_numpy() / interval_s).astype(int)
    g = posts.assign(bin=bins).groupby(['user_id', 'bin'], sort=False)
    table = g.agg(n_posts=('post_id', 'size'), n_words=('word_count', 'sum'))
    table = table[(table['n_words'] >= MIN_WORDS) & (table['n_posts'] >= MIN_POSTS)].reset_index()
    users = np.sort(table['user_id'].unique())
    first = table['bin'].min()
    grid = np.zeros((len(users), table['bin'].max() - first + 1), dtype=np.int16)
    grid[np.searchsorted(users, table['user_id']), table['bin'] - first] = 1
    return users, first, grid.cumsum(axis=1)


def pair_controls(cases, control_posts, rng):
    """Greedy 1:1 pairing without replacement, closest on valid intervals before and after the date."""
    control_users, first_bin, cumulative = calendar_valid(control_posts)
    control_history = by_user(control_posts)
    used = np.zeros(len(control_users), bool)
    pairs, unmatched = [], 0
    for row in cases.sample(frac=1, random_state=rng).itertuples():
        column = int(np.clip(row.index_utc // interval_s - first_bin, 0, cumulative.shape[1] - 1))
        pre, post = cumulative[:, column], cumulative[:, -1] - cumulative[:, column]
        distance = np.abs(np.log1p(pre) - np.log1p(row.n_pre)) + np.abs(np.log1p(post) - np.log1p(row.n_post))
        distance[used | (pre == 0) | (post == 0)] = np.inf
        for i in np.argsort(distance)[:500]:
            if np.isinf(distance[i]):
                break
            found = summary(*control_history[control_users[i]], row.index_utc)
            if found:
                used[i] = True
                pairs.append({'pair_id': len(pairs), 'depression_user': row.user_id, 'control_user': control_users[i],
                              'index_utc': row.index_utc, 'depression_n_pre': row.n_pre, 'depression_n_post': row.n_post,
                              'control_n_pre': found[0], 'control_n_post': found[1]})
                break
        else:
            unmatched += 1
    print(f'paired {len(pairs)}, unmatched {unmatched}', flush=True)
    return pd.DataFrame(pairs)


def interval_table(condition, users_to_index, posts):
    """The notebook's cells 2-3 for one condition's selected users, with anchored bins."""
    table = pq.read_table(DATA / f'final_{condition}_cymo_sentences.parquet', columns=['user_id', 'post_id'] + features,
                          filters=pc.field('user_id').isin(list(users_to_index)))
    sentences = table.to_pandas()
    post_means = sentences.groupby(['user_id', 'post_id'], sort=False)[features].mean().reset_index()
    post_means = post_means.merge(posts[['user_id', 'post_id', 'created_utc', 'word_count']], on=['user_id', 'post_id'])
    index_utc = post_means['user_id'].map(users_to_index)
    post_means['interval'] = np.floor((post_means['created_utc'] - index_utc) / interval_s).astype(int)

    g = post_means.groupby(['user_id', 'interval'])
    intervals = g[features].mean().join(g.agg(n_posts=('post_id', 'size'), n_words=('word_count', 'sum')))
    valid = intervals[(intervals['n_words'] >= MIN_WORDS) & (intervals['n_posts'] >= MIN_POSTS)].reset_index()
    valid.insert(0, 'condition', condition)
    valid.insert(1, 'label', int(condition == 'depression'))
    valid.insert(4, 'period', np.where(valid['interval'] < 0, 'pre', 'post'))
    return valid


def main():
    OUT.mkdir(exist_ok=True)
    rng = np.random.RandomState(SEED)

    depression_posts, control_posts = dated_posts('depression'), dated_posts('control')
    disclosures = pd.read_json(DISCLOSURES, lines=True, dtype={'user_id': int})
    diagnosis = disclosures.groupby('user_id')['created_utc'].min()    # first disclosure stands in for diagnosis

    history = by_user(depression_posts)
    cases = []
    for user, index_utc in diagnosis.items():
        found = summary(*history[user], index_utc) if user in history else None
        if found:
            cases.append({'user_id': user, 'index_utc': index_utc, 'n_pre': found[0], 'n_post': found[1]})
    cases = pd.DataFrame(cases)
    print(f'depression: {len(diagnosis)} with a date, {len(cases)} pass the cohort rules with both periods', flush=True)

    pairs = pair_controls(cases, control_posts, rng)
    pairs['split'] = rng.choice(list(SPLITS), size=len(pairs), p=list(SPLITS.values()))
    pairs.to_csv(OUT / 'pairs.csv', index=False)

    intervals = pd.concat([
        interval_table('depression', dict(zip(pairs['depression_user'], pairs['index_utc'])), depression_posts),
        interval_table('control', dict(zip(pairs['control_user'], pairs['index_utc'])), control_posts),
    ], ignore_index=True)

    # controls and depression users have overlapping ids, so the pair is looked up within each condition
    pair_of = pd.concat([
        pairs.assign(condition='depression', user_id=pairs['depression_user']),
        pairs.assign(condition='control', user_id=pairs['control_user']),
    ])[['condition', 'user_id', 'pair_id', 'split', 'index_utc']]
    intervals = intervals.merge(pair_of, on=['condition', 'user_id'], validate='many_to_one')

    columns = ['split', 'pair_id', 'condition', 'label', 'user_id', 'index_utc', 'period', 'interval', 'n_posts', 'n_words'] + features
    for split in SPLITS:
        part = intervals.loc[intervals['split'] == split, columns]
        part.to_csv(OUT / f'{split}.csv', index=False)
        print(split, part.shape, part.groupby(['period', 'condition']).size().to_dict(), flush=True)


if __name__ == '__main__':
    main()
