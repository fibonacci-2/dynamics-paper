"""Logistic regression on the saved depression vs control splits, scored before and after diagnosis.

Each feature set is one CYMO category from cymo.ipynb, all categories together, or activity volume alone.
C is chosen on the validation split by AUC. Test scores are reported per interval and per user
(a user's probabilities averaged within a period), with 95% CIs from resampling test pairs.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

DATA = Path('data/cymo')
OUT = Path('data/cymo_classification')
RESULTS = Path('results/cymo_classification')

C_GRID = [0.001, 0.01, 0.1, 1, 10]
N_BOOT = 1000
SEED = 42

features = list(json.load(open(DATA / 'float64_features.json'))['features'])
measures = pd.read_csv(DATA / 'cymo_measures.tsv', sep='\t')
groups = (measures[measures['output_column'].isin(features)]
          .groupby('category')['output_column'].apply(list).to_dict())
feature_sets = {**groups, 'All CYMO': features, 'Activity baseline': ['n_posts', 'n_words']}


def model(C):
    return make_pipeline(StandardScaler(), LogisticRegression(C=C, class_weight='balanced', max_iter=2000))


def fit(train, val, columns):
    aucs = {C: roc_auc_score(val['label'], model(C).fit(train[columns], train['label']).predict_proba(val[columns])[:, 1])
            for C in C_GRID}
    best = max(aucs, key=aucs.get)
    return best, model(best).fit(train[columns], train['label'])


def scores(y, p):
    return {'auc': roc_auc_score(y, p), 'accuracy': accuracy_score(y, p >= 0.5),
            'balanced_accuracy': balanced_accuracy_score(y, p >= 0.5), 'f1': f1_score(y, p >= 0.5)}


def bootstrap(frame, rng):
    """Percentile CIs, resampling pairs so a user's intervals and their match stay together."""
    pair_rows = list(frame.groupby('pair_id').indices.values())
    y, p = frame['label'].to_numpy(), frame['p'].to_numpy()
    draws = []
    for _ in range(N_BOOT):
        rows = np.concatenate([pair_rows[i] for i in rng.integers(len(pair_rows), size=len(pair_rows))])
        draws.append(scores(y[rows], p[rows]))
    return pd.DataFrame(draws).quantile([0.025, 0.975])


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    train, val, test = (pd.read_csv(OUT / f'{split}.csv') for split in ['train', 'val', 'test'])

    rows, coefficients = [], []
    for trained_on in ['all', 'pre', 'post']:
        fit_train = train if trained_on == 'all' else train[train['period'] == trained_on]
        fit_val = val if trained_on == 'all' else val[val['period'] == trained_on]
        for name, columns in feature_sets.items():
            C, classifier = fit(fit_train, fit_val, columns)
            scored = test.assign(p=classifier.predict_proba(test[columns])[:, 1])
            if trained_on == 'all':
                coefficients.append(pd.DataFrame({'feature_set': name, 'feature': columns,
                                                  'coefficient': classifier[-1].coef_[0]}))
            for period in ['pre', 'post']:
                intervals = scored[scored['period'] == period]
                users = intervals.groupby(['pair_id', 'condition'], as_index=False).agg(label=('label', 'first'), p=('p', 'mean'))
                for level, frame in {'interval': intervals, 'user': users}.items():
                    ci = bootstrap(frame, rng)
                    row = {'trained_on': trained_on, 'feature_set': name, 'n_features': len(columns), 'C': C,
                           'tested_on': period, 'level': level, 'n': len(frame), 'n_depression': int(frame['label'].sum())}
                    for metric, value in scores(frame['label'].to_numpy(), frame['p'].to_numpy()).items():
                        row |= {metric: value, f'{metric}_low': ci.loc[0.025, metric], f'{metric}_high': ci.loc[0.975, metric]}
                    rows.append(row)
            print(trained_on, name, f'C={C}', flush=True)

    results = pd.DataFrame(rows)
    results.to_csv(RESULTS / 'performance.csv', index=False)
    pd.concat(coefficients).to_csv(RESULTS / 'coefficients.csv', index=False)
    shown = results[results['level'] == 'user'].pivot(index=['trained_on', 'feature_set'], columns='tested_on', values='auc')
    print(shown.round(3).to_string())


if __name__ == '__main__':
    main()
