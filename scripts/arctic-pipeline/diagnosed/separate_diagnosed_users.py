import json
import re
import argparse
import time
import os
import logging

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

# Function to find self-diagnosed users with whitelist handling
def find_self_diagnosed_users(user_data, positive_patterns, negative_patterns, bipolar_synonyms, condition_white):
    diagnosed_users = []
    unique_authors = set()
    synonym_match_counts = {synonym: 0 for synonym in bipolar_synonyms}

    # Count total posts
    total_posts = sum(len(user.get('posts', [])) for user in user_data)
    
    logging.info(f"Processing {len(user_data)} users with {total_posts} total posts")
    logging.info(f"Loaded {len(positive_patterns)} positive patterns")
    logging.info(f"Loaded {len(negative_patterns)} negative patterns")
    logging.info(f"Loaded {len(bipolar_synonyms)} condition synonyms")
    
    # Log first few patterns for debugging
    logging.info(f"First 3 positive patterns: {positive_patterns[:3]}")
    logging.info(f"First 3 condition synonyms: {list(bipolar_synonyms)[:3]}")
    
    posts_with_positive = 0
    posts_with_negative = 0
    posts_with_condition = 0
    posts_with_text = 0
    total_text_length = 0
    post_count = 0

    for user_entry in user_data:
        username = user_entry.get('username', '')
        posts = user_entry.get('posts', [])
        
        if username in unique_authors:
            continue  # Skip if author is already processed
        
        for post in posts:
            post_count += 1
            if post_count % 10000 == 0:
                logging.info(f"Processed {post_count}/{total_posts} posts. Found {len(unique_authors)} diagnosed users so far.")
            
            text = post.get('selftext', '')  # Adjust based on your JSON structure
            author = post.get('author', username)  # Use username if author not in post
            
            # Log first post for debugging
            if post_count == 1:
                logging.info(f"First post keys: {list(post.keys())}")
                logging.info(f"First post text length: {len(text)}")
                logging.info(f"First post text preview: {text[:200] if text else 'EMPTY'}")
            
            if text:
                posts_with_text += 1
                total_text_length += len(text)

            if username in unique_authors:
                continue  # Skip if author is already processed

            bipolar_mentioned = False
            negative_diagnosis_mentioned = False
            positive_diagnosis_mentioned = False

            # Check for negative diagnosis patterns
            for pattern in negative_patterns:
                if re.search(re.escape(pattern), text, re.IGNORECASE):
                    negative_diagnosis_mentioned = True
                    posts_with_negative += 1
                    break

            # Check for positive diagnosis patterns
            for pattern in positive_patterns:
                match = re.search(re.escape(pattern), text, re.IGNORECASE)
                if match:
                    positive_diagnosis_mentioned = True
                    posts_with_positive += 1
                    start_pos = match.start()
                    end_pos = match.end()

                    # Calculate the distance between the positive pattern and bipolar mention
                    for synonym in bipolar_synonyms:
                        if synonym.lower() == "add":  # Special handling for "add"
                            # Check if text matches any entry in the whitelist
                            if any(whitelist_item in text.lower() for whitelist_item in condition_white):
                                bipolar_mentioned = True
                                synonym_match_counts[synonym] += 1
                                posts_with_condition += 1
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
                                posts_with_condition += 1
                                break

            # Only consider users who meet the criteria
            if bipolar_mentioned and not negative_diagnosis_mentioned and positive_diagnosis_mentioned:
                diagnosed_users.append(post)
                unique_authors.add(username)

    logging.info(f"Posts with positive patterns: {posts_with_positive}")
    logging.info(f"Posts with negative patterns: {posts_with_negative}")
    logging.info(f"Posts with condition mention: {posts_with_condition}")
    logging.info(f"Posts with non-empty text: {posts_with_text}/{total_posts}")
    logging.info(f"Average text length: {total_text_length/posts_with_text if posts_with_text > 0 else 0:.1f} chars")
    logging.info(f"Final diagnosed users: {len(unique_authors)}")

    return diagnosed_users, list(unique_authors), synonym_match_counts

def main():
    parser = argparse.ArgumentParser(description='Identify diagnosed users based on their posts.')
    parser.add_argument('input_file', type=str, help='Path to the input JSON file containing cleaned posts')
    parser.add_argument('diagnosed_authors_file', type=str, help='Path to save the diagnosed authors JSON file')
    parser.add_argument('condition_name', type=str, help='Condition name to load patterns for')

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

    # Find self-diagnosed users
    diagnosed_posts, unique_authors, synonym_match_counts = find_self_diagnosed_users(posts_data, positive_patterns, negative_patterns, condition_syns, condition_white)

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
