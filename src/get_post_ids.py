# download_from_df.py
import argparse
import json
import logging
import os
import time

import pandas as pd
from tqdm.auto import tqdm

from arctic_fetch import getpostorcomment


def setup_logging(log_path: str | None):
    handlers = [logging.StreamHandler()]
    if log_path:
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=handlers,
    )


def infer_kind(id_: str) -> str:
    s = str(id_).strip()
    if s.startswith("t1_") or s.startswith("t3_"):
        return "comments" if s.startswith("t1_") else "posts"
    return "comments" if len(s) >= 7 else "posts"


def extract_id_and_author(data):
    obj = data[0] if isinstance(data, list) and data else None
    if not isinstance(obj, dict):
        return None, None
    rid = obj.get("id")
    author = obj.get("author")
    rid = rid.strip() if isinstance(rid, str) else None
    author = author.strip() if isinstance(author, str) else None
    return rid, author


def flush_jsonl(path: str, pending: list[dict]):
    if not pending:
        return
    with open(path, "a", encoding="utf-8") as f:
        for rec in pending:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    pending.clear()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--id_col", default="id", help="Column containing post/comment id")
    ap.add_argument("--out_dir", default="out_authors")
    ap.add_argument("--sleep", type=float, default=0.2)
    ap.add_argument("--save_every", type=int, default=50)
    ap.add_argument("--log", default="download.log")
    args = ap.parse_args()

    setup_logging(args.log)
    os.makedirs(args.out_dir, exist_ok=True)

    df = pd.read_csv(args.csv_path, dtype=str)
    if args.id_col not in df.columns:
        raise SystemExit(f"Missing column: {args.id_col}. Available: {list(df.columns)}")

    ids = df[args.id_col].dropna().astype(str).tolist()
    logging.info("Loaded %d rows from %s (id_col=%s)", len(df), args.csv_path, args.id_col)

    out_path = os.path.join(args.out_dir, "id_to_author.jsonl")
    pending = []
    ok = 0
    fail = 0

    for raw in tqdm(ids, desc="Fetching authors", unit="item"):
        s = str(raw).strip()
        if not s:
            continue
        kind = infer_kind(s)
        try:
            data = getpostorcomment(kind, s)
            rid, author = extract_id_and_author(data)
            if rid is None:
                continue
            pending.append({"id": rid, "author": author, "kind": kind[:-1]})
            ok += 1
            if ok % args.save_every == 0:
                flush_jsonl(out_path, pending)
        except Exception as e:
            fail += 1
            logging.warning("%s %s failed: %s", kind, s, e)
        time.sleep(args.sleep)

    flush_jsonl(out_path, pending)
    logging.info("Done: ok=%d fail=%d output=%s", ok, fail, out_path)


if __name__ == "__main__":
    main()
