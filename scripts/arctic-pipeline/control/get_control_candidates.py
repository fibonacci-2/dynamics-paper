import json
import requests
import argparse
import urllib3
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def globalSettings(settings_file='../../../../config/global.json'):
    with open(settings_file, 'r', encoding='utf-8') as file:
        settings = json.load(file)
    return settings

formatted_json = json.dumps(globalSettings(), indent=4)
formatted_json = formatted_json.replace('{', '').replace('}', '').replace('"', '').strip()
print("")
print("Settings: ")
print(formatted_json)
print("")

# Suppress only the single InsecureRequestWarning from urllib3 needed to remove warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def fetch_posts(subreddit, limit):
    url = f'https://arctic-shift.photon-reddit.com/api/posts/search?subreddit={subreddit}&limit={limit}'
    retries = 8
    delay = 1

    for attempt in range(retries):
        try:
            response = requests.get(url, verify=False)
            response.raise_for_status()  # Will raise an HTTPError for bad responses (4xx and 5xx)
            return response.json().get('data', [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching posts for subreddit {subreddit}. Error: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2  # Exponential backoff

    print(f"Failed to fetch posts for subreddit {subreddit} after {retries} attempts.")
    return []

def fetch_posts_for_subreddits(subreddits, limit):
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_posts, subreddit, limit): subreddit for subreddit in subreddits}
        results = {}
        for future in as_completed(futures):
            subreddit = futures[future]
            try:
                results[subreddit] = future.result()
            except Exception as e:
                print(f"Error fetching posts for subreddit {subreddit}: {e}")
                results[subreddit] = []
        return results

def expand_users_with_candidates(diagnosed_users):
    expanded_users = []
    total_candidates = 0  # To keep track of the total number of candidate usernames

    for user in diagnosed_users:
        username = user['username']
        non_mh_subreddits = user['non_mental_health_subreddits']
        candidate_usernames = set()

        subreddit_posts = fetch_posts_for_subreddits(non_mh_subreddits, 100)

        for subreddit, posts in subreddit_posts.items():
            authors = {post['author'] for post in posts if 'author' in post}
            candidate_usernames.update(authors)

        expanded_user_data = {
            'username': username,
            'post_count': user['post_count'],
            'non_mental_health_subreddits': non_mh_subreddits,
            'candidate_usernames': list(candidate_usernames)
        }

        expanded_users.append(expanded_user_data)
        total_candidates += len(candidate_usernames)
        print(f"Processed user {username} with {len(candidate_usernames)} candidate usernames")

    average_candidates_per_user = total_candidates / len(diagnosed_users) if diagnosed_users else 0
    print("")
    print("---------------------summary-------------------------")
    print(f"Average number of candidate controls per diagnosed user: {average_candidates_per_user:.2f}")

    return expanded_users

def main():
    parser = argparse.ArgumentParser(description='Expand diagnosed users with candidate control usernames.')
    parser.add_argument('input_file', type=str, help='Path to the input JSON file containing diagnosed users')
    parser.add_argument('output_file', type=str, help='Path to save the expanded JSON file')

    args = parser.parse_args()

    start_time = time.time()  # Start timing

    diagnosed_users = load_json(args.input_file)

    expanded_users = expand_users_with_candidates(diagnosed_users)

    output_dir = os.path.dirname(args.output_file)
    os.makedirs(output_dir, exist_ok=True)

    with open(args.output_file, 'w', encoding='utf-8') as file:
        json.dump(expanded_users, file, indent=4)

if __name__ == '__main__':
    main()
