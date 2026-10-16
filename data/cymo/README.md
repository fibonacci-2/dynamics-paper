# CYMO annotations of the final files

CYMO (EXAIA CYMO v1.0.0-beta) features for every post and comment in the `final_<condition>.csv` files (one folder up),
the cleaned everyday-language subset of each user's history. These are the same posts as
`LIWC_Annotations/final_<condition>_liwc.parquet`. CYMO scores every **sentence** on 344 measures. Built 4 October 2026
from the CYMO output files.

## Files

| File | One row per | Contents |
|---|---|---|
| `final_<cond>_cymo_sentences.parquet` | sentence | `user_id`, `post_id`, `wid` (sentence number within the post, from 0), and the 344 measures exactly as CYMO returned them |
| `cymo_measures.tsv` | measure | code, column name, name, category, subcategory and definition of each measure, from the CYMO documentation (cymo-doc.exaia-tech.net) |
| `float64_features.json` | | the decimal measures stored as float64 (see Values) |
| `build_log.json` | condition | the checks below, per condition |
| `SHA256SUMS.txt` | file | checksums, to confirm a download is intact |

There are no post-level files: one row per post is a quick average of the sentence file (see One row per post).

## What is here

| Condition | Sentences | Posts | Users | Posts without a timestamp | File |
|---|--:|--:|--:|--:|--:|
| ADHD | 18,959,033 | 3,912,788 | 17,082 | 18,933 (0.5%) | 6.93 GB |
| Anxiety | 3,167,448 | 636,891 | 3,218 | 3,856 (0.6%) | 1.15 GB |
| Autism | 8,761,026 | 1,836,666 | 8,455 | 51,522 (2.8%) | 3.22 GB |
| Bipolar | 5,729,547 | 1,145,442 | 6,344 | 2,288 (0.2%) | 2.06 GB |
| Depression | 4,476,391 | 933,025 | 5,401 | 1,529 (0.2%) | 1.62 GB |
| OCD | 1,727,514 | 371,034 | 2,081 | 35,303 (9.5%) | 0.63 GB |
| PTSD | 1,624,139 | 316,186 | 1,814 | 2,353 (0.7%) | 0.59 GB |
| Control | 67,125,508 | 19,511,619 | 108,827 | 7,939,607 (40.7%) | 23.68 GB |

The sentence files total 39.9 GB, against
150.8 GB of CYMO's original CSV output. "Posts without a timestamp" is explained under Joining to other data.

Checks, all passed for every condition:
- every CYMO output file's first and last post ID match the upload manifest;
- the number of posts equals the number of posts sent to CYMO;
- no post appears twice;
- each user's rows are contiguous: the upload had to be cut into parts under 200 MB, and the cuts sometimes fell inside a
  user's posts, so the parts were joined back into one file per condition.

## Loading

The files are Parquet: compressed, typed, and readable one column at a time.

Python (pandas needs `pyarrow`, already installed in Colab and Anaconda):

```python
import pandas as pd
# load only the columns you need: Control has 67 million sentences
s = pd.read_parquet("final_depression_cymo_sentences.parquet", columns=["user_id", "post_id", "wid", "PRNp1s", "MLS"])
```

DuckDB (SQL on the file, without loading it all into memory):

```python
import duckdb
duckdb.sql("SELECT user_id, avg(PRNp1s) AS i_per_sentence FROM 'final_adhd_cymo_sentences.parquet' GROUP BY user_id").df()
```

R:

```r
library(arrow)
s <- read_parquet("final_depression_cymo_sentences.parquet", col_select = c("user_id", "post_id", "wid", "PRNp1s"))
```

## One row per post

Most analyses work per post, like the timestamps and LIWC. Average each post's sentences. For a few measures this takes
seconds, even for ADHD:

```python
import pandas as pd
cols = ["PRNp1s", "MLS", "EMOsad"]                       # the measures you need
s = pd.read_parquet("final_adhd_cymo_sentences.parquet", columns=["user_id", "post_id"] + cols)
g = s.groupby(["user_id", "post_id"], sort=False)
posts = g[cols].mean().join(g.size().rename("n_sent")).reset_index()
```

- `n_sent` is the number of sentences in the post. For a count measure, the post total is the mean × `n_sent` (or use
  `.sum()` instead of `.mean()`); for example, `MLS` × `n_sent` is the post's word count.
- All 344 measures at once take a lot of memory for the larger conditions; load a group of measures at a time.

## Values

- **Counts** (109 measures, e.g. `PRNp1s` = first-person singular pronouns, `EMOsad` = sadness words): whole numbers per
  sentence, stored as int16, exact.
- **Decimals** (235 measures): CYMO writes them with 4 decimal places. The 44 that reach 512 or more in absolute
  value are stored as float64 and are exact. The rest are stored as float32, which can display extra digits
  (7.3333 shows as 7.33330011); `df.round(4)` gives CYMO's exact values. This was checked for every value.
- Three column names differ in letter case from the documentation's codes: `FryX`, `FryY` and `N2SAdvOb`
  (see `cymo_measures.tsv`, column `output_column`).
- Emotion measures, valence per the CYMO documentation:
  - positive: `EMOacc`, `EMOant`, `EMObli`, `EMOcal`, `EMOcon`, `EMOdel`, `EMOeag`, `EMOecs`, `EMOent`, `EMOjoy`, `EMOlov`,
    `EMOple`, `EMOres`, `EMOser`, `EMOtru`;
  - negative: `EMOang`, `EMOann`, `EMOanx`, `EMOdsg`, `EMOdsl`, `EMOfea`, `EMOgri`, `EMOloa`, `EMOmel`, `EMOrag`, `EMOsad`,
    `EMOter`;
  - neutral: `EMOsur`.

## Joining to other data

- **Keys.** Join on `user_id` + `post_id`.
  - `user_id` is the numeric user ID of the final files. It is stored here as an integer but as text in the LIWC files,
    so convert it before joining: `posts["user_id"] = posts["user_id"].astype(str)`.
  - The seven diagnosed conditions share one numbering. The controls use a separate numbering that overlaps it, so
    across conditions always key on condition + `user_id`.
- **Time and subreddit.** CYMO's output carries neither. Join `created_utc`, `subreddit` and `type` (post or comment)
  from `LIWC_Annotations/metadata_<cond>_liwc.parquet`.
  - That file has no row for 115,784 of the diagnosed conditions' posts (1.3%), from 342 users;
    see the table under What is here. For controls the gap is larger, 7,939,607 posts (40.7%): 44,232 of the 108,827 control users have no row in it at all. Those posts get no timestamp from it.
- **What the final files leave out.** They cover about 12% of each history, up to 2024. Posts that name a condition or say
  "diagnos*", and the diagnosis-disclosure posts, were removed upstream, so this data has no disclosure posts.

## Please note

`post_id` is the original Reddit ID, so a post can be looked up on Reddit and traced to its author. Keep these files within
the project team.
