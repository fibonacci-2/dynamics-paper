"""Pull the metadata columns out of the full JSONL files, without the post text."""
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.json as pj
import pyarrow.parquet as pq

OUT = Path('data/cymo_classification')
SCHEMA = pa.schema([('post_id', pa.string()), ('user_id', pa.string()), ('created_utc', pa.float64()),
                    ('word_count', pa.float64()), ('type', pa.string()), ('subreddit', pa.string())])

OUT.mkdir(exist_ok=True)
for condition in ['depression', 'control']:
    start = time.time()
    reader = pj.open_json(f'data/final_{condition}_full_metadata.jsonl',
                          read_options=pj.ReadOptions(block_size=512 << 20),
                          parse_options=pj.ParseOptions(explicit_schema=SCHEMA, unexpected_field_behavior='ignore'))
    rows = 0
    with pq.ParquetWriter(OUT / f'metadata_{condition}.parquet', SCHEMA) as writer:
        for batch in reader:
            writer.write_batch(batch)
            rows += batch.num_rows
    print(condition, rows, f'{time.time() - start:.0f}s', flush=True)
