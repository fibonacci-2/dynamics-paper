import json
import re
import argparse
import time
import os
import logging
from multiprocessing import Pool, Manager
from functools import partial

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to load JSON data from a file
def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

# Function to load patterns from a text file and expand placeholders
def load_patterns(file_path, expansions):
    with open(file_path, 'r') as file:
        patterns = []
        for line in file.readlines():
            pattern = line.strip()
            for placeholder, replacements in expansions.items():
                if placeholder in pattern:
                    # Replace the placeholder with each replacement, creating new patterns
                    patterns.extend(pattern.replace(placeholder, replacement) for replacement in replacements)
                    break
            else:
                # If no placeholder is found, add the pattern as-is
                patterns.append(pattern)
        return patterns

# Function to load expansions from a JSON file
def load_expansions(file_path):
    return load_json(file_path)

# Process a single user's posts and return diagnosed status
def process_user(user_entry, positive_patterns, negative_patterns, bipolar_synonyms, condition_white):
    """Process a single user and return diagnosed posts if user meets criteria."""
    username = user_entry.get('username', '')
    posts = user_entry.get('posts', [])
    diagnosed_posts = []
    is_diagnosed = False
    synonym_match_counts = {synonym: 0 for synonym in bipolar_synonyms}
    
    for post in posts:
        text = post.get('selftext', '')
        author = post.get('author', username)
        
        bipolar_mentioned = False
        negative_diagnosis_mentioned = False
        positive_diagnosis_mentioned = False

        # Check for negative diagnosis patterns
        for pattern in negative_patterns:
            if re.search(re.escape(pattern), text, re.IGNORECASE):
                negative_diagnosis_mentioned = True
                break

        # Check for positive diagnosis patterns
        for pattern in positive_patterns:
            match = re.search(re.escape(pattern), text, re.IGNORECASE)
            if match:
                positive_diagnosis_mentioned = True
                start_pos = match.start()
                end_pos = match.end()

                # Calculate the distance between the positive pattern and bipolar mention
                for synonym in bipolar_synonyms:
                    if synonym.lower() == "add":  # Special handling for "add"
                        # Check if text matches any entry in the whitelist
                        if any(whitelist_item in text.lower() for whitelist_item in condition_white):
                            bipolar_mentioned = True
                            synonym_match_counts[synonym] += 1
                            break
                        # Otherwise, require context like "attention deficit"
                        add_context_pattern = r"(attention\s+deficit|adhd)"
                        context_match = re.search(add_context_pattern, text, re.IGNORECASE)
                        if not context_match:
                            continue  # Skip "add" if context is not found

                    synonym_match = re.search(r'\b' + re.escape(synonym) + r'\b', text, re.IGNORECASE)
                    if synonym_match:
                        synonym_start_pos = synonym_match.start()
                        synonym_end_pos = synonym_match.end()
                        distance = min(abs(start_pos - synonym_end_pos), abs(end_pos - synonym_start_pos))
                        if distance <= 40:
                            bipolar_mentioned = True
                            synonym_match_counts[synonym] += 1
                            break

        # Only consider users who meet the criteria
        if bipolar_mentioned and not negative_diagnosis_mentioned and positive_diagnosis_mentioned:
            diagnosed_posts.append(post)
            is_diagnosed = True
    
    return {
        'username': username,
        'is_diagnosed': is_diagnosed,
        'diagnosed_posts': diagnosed_posts,
        'synonym_counts': synonym_match_counts
    }


# Function to find self-diagnosed users with whitelist handling using multiprocessing
def find_self_diagnosed_users(user_data, positive_patterns, negative_patterns, bipolar_synonyms, condition_white, num_cores=40):
    # Count total posts
    total_posts = sum(len(user.get('posts', [])) for user in user_data)
    
    logging.info(f"Processing {len(user_data)} users with {total_posts} total posts using {num_cores} cores")
    logging.info(f"Loaded {len(positive_patterns)} positive patterns")
    logging.info(f"Loaded {len(negative_patterns)} negative patterns")
    logging.info(f"Loaded {len(bipolar_synonyms)} condition synonyms")
    
    # Log first few patterns for debugging
    logging.info(f"First 3 positive patterns: {positive_patterns[:3]}")
    logging.info(f"First 3 condition synonyms: {list(bipolar_synonyms)[:3]}")
    
    # Create a partial function with fixed arguments
    process_user_partial = partial(
        process_user,
        positive_patterns=positive_patterns,
        negative_patterns=negative_patterns,
        bipolar_synonyms=bipolar_synonyms,
        condition_white=condition_white
    )
    
    # Use multiprocessing to process users in parallel
    diagnosed_users = []
    unique_authors = set()
    synonym_match_counts = {synonym: 0 for synonym in bipolar_synonyms}
    
    logging.info(f"Starting parallel processing with {num_cores} workers...")
    start_pool_time = time.time()
    
    with Pool(processes=num_cores) as pool:
        results = pool.map(process_user_partial, user_data, chunksize=max(1, len(user_data) // (num_cores * 4)))
    
    pool_time = time.time() - start_pool_time
    logging.info(f"Parallel processing completed in {pool_time:.2f} seconds")
    
    # Aggregate results
    for result in results:
        if result['is_diagnosed']:
            unique_authors.add(result['username'])
            diagnosed_users.extend(result['diagnosed_posts'])
            # Aggregate synonym counts
            for synonym, count in result['synonym_counts'].items():
                synonym_match_counts[synonym] += count
    
    logging.info(f"Final diagnosed users: {len(unique_authors)}")

    return diagnosed_users, list(unique_authors), synonym_match_counts

def main():
    parser = argparse.ArgumentParser(description='Identify diagnosed users based on their posts.')
    parser.add_argument('input_file', type=str, help='Path to the input JSON file containing cleaned posts')
    parser.add_argument('diagnosed_authors_file', type=str, help='Path to save the diagnosed authors JSON file')
    parser.add_argument('condition_name', type=str, help='Condition name to load patterns for')
    parser.add_argument('num_cores', type=int, help='Number of cores to launch on')
    args = parser.parse_args()

    # Hardcoded paths to the pattern text files
    patterns_dir = '../../../resources/'
    positive_patterns_file = os.path.join(patterns_dir, 'positive_diagnosis_patterns.txt')
    negative_patterns_file = os.path.join(patterns_dir, 'negative_diagnosis_patterns.txt')
    bipolar_synonyms_file = os.path.join(patterns_dir, f'conditions/{args.condition_name}-syns.txt')
    bipolar_white_synonyms_file = os.path.join(patterns_dir, f'conditions/{args.condition_name}-white.txt')
    expansions_file = os.path.join(patterns_dir, 'expansions.json')

    # Load the expansions from JSON
    expansions = load_expansions(expansions_file)

    # Load the patterns and expand placeholders
    positive_patterns = load_patterns(positive_patterns_file, expansions)
    negative_patterns = load_patterns(negative_patterns_file, expansions)
    # print(positive_patterns)
    # Load synonyms and whitelist
    condition_syns = load_patterns(bipolar_synonyms_file, {})
    condition_white = load_patterns(bipolar_white_synonyms_file, {})

    # Load posts data
    posts_data = load_json(args.input_file)

    # Start timing the diagnosis process
    start_time = time.time()

    # Find self-diagnosed users with 40 cores
    diagnosed_posts, unique_authors, synonym_match_counts = find_self_diagnosed_users(posts_data, positive_patterns, negative_patterns, condition_syns, condition_white, args.num_cores)

    # End timing the diagnosis process
    end_time = time.time()
    elapsed_time = end_time - start_time

    print(f"{len(unique_authors)} users diagnosed in {elapsed_time:.2f} seconds. Saved to {args.diagnosed_authors_file}")

    # Save unique authors to a JSON file
    try:
        with open(args.diagnosed_authors_file, 'w') as f:
            json.dump(unique_authors, f, indent=4)
        print(f"Diagnosed authors saved to {args.diagnosed_authors_file}")
    except Exception as e:
        print(f"Error saving diagnosed authors: {e}")

    # Save diagnosed posts
    diagnosed_dir = os.path.dirname(args.diagnosed_authors_file)
    diagnosed_posts_file = os.path.join(diagnosed_dir, 'diagnosed_posts.json')

    try:
        with open(diagnosed_posts_file, 'w', encoding='utf-8') as f:
            json.dump(diagnosed_posts, f, indent=4)
        print(f"Diagnosed posts saved to {diagnosed_posts_file}")
    except Exception as e:
        print(f"Error saving diagnosed posts: {e}")

    # Save synonym match counts
    synonym_counts_file = os.path.join(diagnosed_dir, 'synonym_match_counts.json')

    try:
        with open(synonym_counts_file, 'w', encoding='utf-8') as f:
            json.dump(synonym_match_counts, f, indent=4)
        print(f"Synonym match counts saved to {synonym_counts_file}")
    except Exception as e:
        print(f"Error saving synonym match counts: {e}")

if __name__ == '__main__':
    main()
