#!/usr/bin/env python3
import json
import re
import argparse
import time
import os
import logging
import multiprocessing as mp
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional
from functools import partial

from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# -----------------------------
# IO helpers
# -----------------------------
def load_json(file_path: str):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)

def load_patterns(file_path: str, expansions: Dict[str, List[str]]):
    with open(file_path, "r", encoding="utf-8") as file:
        patterns = []
        for line in file:
            pattern = line.strip()
            if not pattern:
                continue
            expanded = False
            for placeholder, replacements in expansions.items():
                if placeholder in pattern:
                    patterns.extend(pattern.replace(placeholder, r) for r in replacements)
                    expanded = True
                    break
            if not expanded:
                patterns.append(pattern)
        return patterns

def load_expansions(file_path: str):
    return load_json(file_path)

# -----------------------------
# Worker globals (compiled once per process)
# -----------------------------
_POS_RE = None
_NEG_RE = None
_SYN_RE = None
_ADD_CTX_RE = None
_WHITE = None
_MAX_DIST = 40
_RETURN_MINIMAL_POSTS = True

def _compile_literal_patterns(patterns: List[str]) -> List[re.Pattern]:
    # Your original used re.escape(pattern) which makes them literal anyway.
    # Compile once for speed.
    out = []
    for p in patterns:
        if not p:
            continue
        out.append(re.compile(re.escape(p), re.IGNORECASE))
    return out

def _compile_word_boundary_synonyms(syns: List[str]) -> Dict[str, re.Pattern]:
    # Compile each synonym once with word boundaries
    d = {}
    for s in syns:
        s2 = (s or "").strip()
        if not s2:
            continue
        d[s2] = re.compile(r"\b" + re.escape(s2) + r"\b", re.IGNORECASE)
    return d

def worker_init(positive_patterns, negative_patterns, condition_syns, condition_white,
                max_dist: int, return_minimal_posts: bool):
    global _POS_RE, _NEG_RE, _SYN_RE, _ADD_CTX_RE, _WHITE, _MAX_DIST, _RETURN_MINIMAL_POSTS
    _POS_RE = _compile_literal_patterns(positive_patterns)
    _NEG_RE = _compile_literal_patterns(negative_patterns)
    _SYN_RE = _compile_word_boundary_synonyms(condition_syns)
    _WHITE = set([w.strip().lower() for w in condition_white if w.strip()])
    _ADD_CTX_RE = re.compile(r"(attention\s+deficit|adhd)", re.IGNORECASE)
    _MAX_DIST = int(max_dist)
    _RETURN_MINIMAL_POSTS = bool(return_minimal_posts)

# -----------------------------
# Core logic (runs in workers)
# -----------------------------
def process_user(user_entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Returns a SMALL result dict to avoid BrokenPipe from huge IPC payloads.
    If user is not diagnosed => returns None.
    """
    try:
        username = user_entry.get("username", "") or ""
        posts = user_entry.get("posts", []) or []

        diagnosed_posts = []
        synonym_counts = {syn: 0 for syn in _SYN_RE.keys()}
        is_diagnosed = False

        for post in posts:
            text = post.get("selftext", "") or ""
            text_l = text.lower()

            # 1) Negative diagnosis?
            negative = any(r.search(text) for r in _NEG_RE)
            if negative:
                continue

            # 2) Positive diagnosis? (find first match position)
            pos_match = None
            for r in _POS_RE:
                m = r.search(text)
                if m:
                    pos_match = m
                    break
            if not pos_match:
                continue

            start_pos, end_pos = pos_match.start(), pos_match.end()

            # 3) Condition mention nearby?
            bipolar_mentioned = False
            for syn, syn_re in _SYN_RE.items():
                # Special handling for ADD
                if syn.lower() == "add":
                    # whitelist override
                    if any(w in text_l for w in _WHITE):
                        bipolar_mentioned = True
                        synonym_counts[syn] += 1
                        break
                    # otherwise require context like "attention deficit" or "adhd"
                    if not _ADD_CTX_RE.search(text):
                        continue

                m2 = syn_re.search(text)
                if not m2:
                    continue

                s2, e2 = m2.start(), m2.end()
                distance = min(abs(start_pos - e2), abs(end_pos - s2))
                if distance <= _MAX_DIST:
                    bipolar_mentioned = True
                    synonym_counts[syn] += 1
                    break

            if bipolar_mentioned:
                is_diagnosed = True
                if _RETURN_MINIMAL_POSTS:
                    diagnosed_posts.append({
                        "id": post.get("id"),
                        "author": post.get("author", username),
                        "created_utc": post.get("created_utc"),
                        "selftext": post.get("selftext", ""),
                        "title": post.get("title", ""),
                        "subreddit": post.get("subreddit", ""),
                        "permalink": post.get("permalink", ""),
                    })
                else:
                    diagnosed_posts.append(post)

        if not is_diagnosed:
            return None

        return {
            "username": username,
            "diagnosed_posts": diagnosed_posts,
            "synonym_counts": synonym_counts,
        }

    except Exception as e:
        # Do not crash a worker; return a sentinel
        return {"__error__": str(e)}

# -----------------------------
# Parallel runner (streaming)
# -----------------------------
def find_self_diagnosed_users(
    user_data: List[Dict[str, Any]],
    positive_patterns: List[str],
    negative_patterns: List[str],
    condition_syns: List[str],
    condition_white: List[str],
    num_cores: int,
    max_dist: int = 40,
    return_minimal_posts: bool = True,
) -> Tuple[List[Dict[str, Any]], List[str], Dict[str, int], int]:

    total_posts = sum(len(u.get("posts", []) or []) for u in user_data)
    logging.info(f"Processing {len(user_data):,} users with {total_posts:,} total posts using {num_cores} cores")
    logging.info(f"Loaded {len(positive_patterns)} positive patterns")
    logging.info(f"Loaded {len(negative_patterns)} negative patterns")
    logging.info(f"Loaded {len(condition_syns)} condition synonyms")

    diagnosed_posts_all: List[Dict[str, Any]] = []
    unique_authors = set()
    synonym_match_counts = {syn: 0 for syn in condition_syns if syn.strip()}
    n_errors = 0

    # Safer start method on HPC
    try:
        mp.set_start_method("forkserver", force=True)
    except RuntimeError:
        pass

    chunksize = max(16, len(user_data) // max(1, num_cores * 8))
    logging.info(f"Starting parallel processing (chunksize={chunksize}, maxtasksperchild=2000)...")

    start_pool_time = time.time()

    with mp.Pool(
        processes=num_cores,
        initializer=worker_init,
        initargs=(positive_patterns, negative_patterns, condition_syns, condition_white, max_dist, return_minimal_posts),
        maxtasksperchild=2000,
    ) as pool:
        # STREAM results to avoid buffering everything (prevents huge memory + pipe pressure)
        for res in tqdm(pool.imap_unordered(process_user, user_data, chunksize=chunksize),
                        total=len(user_data), desc="Users", unit="user"):
            if res is None:
                continue
            if "__error__" in res:
                n_errors += 1
                continue

            unique_authors.add(res["username"])
            diagnosed_posts_all.extend(res["diagnosed_posts"])

            for syn, c in res["synonym_counts"].items():
                synonym_match_counts[syn] = synonym_match_counts.get(syn, 0) + int(c)

    pool_time = time.time() - start_pool_time
    logging.info(f"Parallel processing completed in {pool_time:.2f} seconds")
    logging.info(f"Final diagnosed users: {len(unique_authors):,}")
    if n_errors:
        logging.warning(f"Worker errors encountered (suppressed to avoid crashing): {n_errors:,}")

    return diagnosed_posts_all, list(unique_authors), synonym_match_counts, n_errors

# -----------------------------
# Main
# -----------------------------
def main():
    parser = argparse.ArgumentParser(description="Identify diagnosed users based on their posts.")
    parser.add_argument("input_file", type=str, help="Path to the input JSON file containing cleaned posts")
    parser.add_argument("diagnosed_authors_file", type=str, help="Path to save the diagnosed authors JSON file")
    parser.add_argument("condition_name", type=str, help="Condition name to load patterns for")
    parser.add_argument("num_cores", type=int, help="Number of cores to launch on")
    parser.add_argument("--max-dist", type=int, default=40, help="Max char distance between diagnosis phrase and synonym")
    parser.add_argument("--full-posts", action="store_true",
                        help="Return full post objects (bigger memory/IPC). Default returns minimal post fields.")
    args = parser.parse_args()

    patterns_dir = "../../../resources/"
    positive_patterns_file = os.path.join(patterns_dir, "positive_diagnosis_patterns.txt")
    negative_patterns_file = os.path.join(patterns_dir, "negative_diagnosis_patterns.txt")
    condition_syns_file = os.path.join(patterns_dir, f"conditions/{args.condition_name}-syns.txt")
    condition_white_file = os.path.join(patterns_dir, f"conditions/{args.condition_name}-white.txt")
    expansions_file = os.path.join(patterns_dir, "expansions.json")

    expansions = load_expansions(expansions_file)
    positive_patterns = load_patterns(positive_patterns_file, expansions)
    negative_patterns = load_patterns(negative_patterns_file, expansions)
    condition_syns = load_patterns(condition_syns_file, {})
    condition_white = load_patterns(condition_white_file, {})

    logging.info("Loading posts JSON...")
    posts_data = load_json(args.input_file)

    start_time = time.time()

    diagnosed_posts, unique_authors, synonym_match_counts, n_errors = find_self_diagnosed_users(
        posts_data,
        positive_patterns,
        negative_patterns,
        condition_syns,
        condition_white,
        num_cores=args.num_cores,
        max_dist=args.max_dist,
        return_minimal_posts=not args.full_posts,
    )

    elapsed_time = time.time() - start_time
    print(f"{len(unique_authors):,} users diagnosed in {elapsed_time:.2f} seconds. Saved to {args.diagnosed_authors_file}")
    if n_errors:
        print(f"Note: suppressed {n_errors:,} worker errors (see logs).")

    diagnosed_dir = os.path.dirname(args.diagnosed_authors_file) or "."
    os.makedirs(diagnosed_dir, exist_ok=True)

    # Save unique authors
    with open(args.diagnosed_authors_file, "w", encoding="utf-8") as f:
        json.dump(unique_authors, f, ensure_ascii=False, indent=2)

    # Save diagnosed posts
    diagnosed_posts_file = os.path.join(diagnosed_dir, "diagnosed_posts.json")
    with open(diagnosed_posts_file, "w", encoding="utf-8") as f:
        json.dump(diagnosed_posts, f, ensure_ascii=False, indent=2)

    # Save synonym match counts
    synonym_counts_file = os.path.join(diagnosed_dir, "synonym_match_counts.json")
    with open(synonym_counts_file, "w", encoding="utf-8") as f:
        json.dump(synonym_match_counts, f, ensure_ascii=False, indent=2)

    print(f"Diagnosed posts saved to {diagnosed_posts_file}")
    print(f"Synonym match counts saved to {synonym_counts_file}")


if __name__ == "__main__":
    main()
