
import json
import glob
import pandas as pd
import json

condition = 'adhd'
df = pd.read_csv(f'~/Downloads/Copy of final_adhd.csv')
print(df.head())

#get id map
id_map = {}
with open("/SEAS/home/g21775526/Downloads/adhd_usernames.json", 'r', encoding='utf-8') as f:
    data = json.load(f)          # each file is a dict: { "100067": "Txmttxmt", ... }
    id_map.update(data)          # later files overwrite duplicates if any
 

df['user_id_string'] = df.apply(lambda row: id_map.get(str(row['user_id'])), axis=1)
unique_users = df['user_id_string'].unique()

print(f"usrs with no ids {df['user_id_string'].isna().sum()}")
print(40*'-')

import json
import requests
import os
import urllib3
from tqdm import tqdm
MIN_POSTS = 50

# Disable the InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Function to load unique users from a JSON file
def load_unique_users(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

# Function to fetch user submissions from Arctic Shift API
def fetch_user_submissions(username):
    posts_url = f'https://arctic-shift.photon-reddit.com/api/posts/search?author={username}&limit=auto'
    comments_url = f'https://arctic-shift.photon-reddit.com/api/comments/search?author={username}&limit=auto'

    posts, comments = [], []

    try:
        # Fetch posts
        posts_response = requests.get(posts_url, verify=False)  # Disable SSL verification
        posts_response.raise_for_status()  # Raise an exception for HTTP errors
        posts = posts_response.json().get('data', [])

        # Fetch comments
        comments_response = requests.get(comments_url, verify=False)  # Disable SSL verification
        comments_response.raise_for_status()  # Raise an exception for HTTP errors
        comments = comments_response.json().get('data', [])

        # Adjust comments to use 'selftext' instead of 'body'
        for comment in comments:
            comment['selftext'] = comment.pop('body', '')

    except Exception as e:
        print(f"Failed to fetch data for user {username}. Error: {e}")

    return posts + comments

# Main function to process all unique users
def main():
    output_file = f"~/Downloads/{condition}_all_submissions.json"

    all_user_submissions = []
    total_posts = 0
    qualified_users_count = 0

    for user in tqdm(unique_users, desc="fetching users submissions..."):
        # print(f"Processing user: {user}")
        submissions = fetch_user_submissions(user)
        # print(f"fetched submisisons: {len(submissions)}")

        if submissions:
            # Filter submissions to only include those with text content
            posts = [submission for submission in submissions if submission.get('selftext') is not None]
            if len(posts) >= MIN_POSTS:
                all_user_submissions.append({
                    'username': user,
                    'posts': posts
                })
                total_posts += len(posts)
                qualified_users_count += 1

                # print(f"---{user} > {len(posts)}")

    # Save all user submissions to a single JSON file
    with open(output_file, 'w') as f:
        json.dump(all_user_submissions, f, indent=4)

    # Calculate average number of posts per user
    if qualified_users_count > 0:
        average_posts = total_posts / qualified_users_count
    else:
        average_posts = 0

    print("")
    # print(f"{qualified_users_count}/{len(unique_users)} diagnosed users meeting minimum activity of {threshold} posts")
    print(f"Average number of posts per qualified user: {average_posts:.2f}")

if __name__ == '__main__':
    main()

