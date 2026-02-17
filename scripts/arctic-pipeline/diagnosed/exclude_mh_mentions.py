import json
import re
import argparse

def globalSettings(settings_file='../../../../config/global.json'):
    with open(settings_file, 'r', encoding='utf-8') as file:
        settings = json.load(file)
    return settings

# Function to load patterns from a text file
def load_patterns(file_path):
    with open(file_path, 'r') as file:
        return [line.strip().lower() for line in file.readlines()]

# Function to check if a post contains any mental health patterns
def contains_mental_health_patterns(text, patterns):
    text = text.lower()
    return any(re.search(re.escape(pattern), text) for pattern in patterns)

# Function to remove posts with mental health patterns and ensure selftext is valid
def remove_mental_health_posts(posts, mental_health_patterns):
    return [
        post for post in posts
        if not contains_mental_health_patterns(post.get('selftext', ''), mental_health_patterns)
        and post.get('selftext') not in ['', '[removed]']
    ]

# Main function to process all unique users
def main():
    parser = argparse.ArgumentParser(
        description='Filter and remove mental health-related Reddit posts.')
    parser.add_argument('input_file', type=str,
                        help='Path to the input JSON file containing user submissions')
    parser.add_argument('output_file', type=str,
                        help='Path to save the filtered JSON file')
    parser.add_argument('summary_file', type=str,
                        help='Path to save the summary JSON file')


    args = parser.parse_args()

    # Hardcoded path to the mental health patterns text file
    mental_health_patterns_file = '../../../resources/mh_patterns.txt'
    mental_health_patterns = load_patterns(mental_health_patterns_file)

    user_submissions = []
    with open(args.input_file, 'r', encoding='utf-8') as file:
        user_submissions = json.load(file)

    all_user_submissions = []
    user_post_counts = []
    total_posts = 0
    qualified_users_count = 0
    non_qualified_users_count = 0
    non_mh_threshold = globalSettings()["non_mh_posts_per_diagnosed_user"]

    for submission in user_submissions:
        posts = submission['posts']
        filtered_posts = remove_mental_health_posts(posts, mental_health_patterns)
        if filtered_posts and len(filtered_posts) >= non_mh_threshold:
            all_user_submissions.append({
                'username': submission['username'],
                'posts': filtered_posts
            })
            total_posts += len(filtered_posts)
            qualified_users_count += 1
            user_post_counts.append({
                'username': submission['username'],
                'post_count': len(filtered_posts),
                'non_mental_health_subreddits': list({post['subreddit'] for post in filtered_posts if post.get('subreddit')})
            })
        else:
            non_qualified_users_count += 1


        print(f"Processed user {submission['username']} with              {len(filtered_posts)} posts")

    # Save all user submissions to a single JSON file
    with open(args.output_file, 'w', encoding='utf-8') as file:
        json.dump(all_user_submissions, file, indent=4)

    # Save user post counts to the summary file
    with open(args.summary_file, 'w', encoding='utf-8') as file:
        json.dump(user_post_counts, file, indent=4)

    # Calculate average number of posts per user
    if qualified_users_count > 0:
        average_posts = total_posts / qualified_users_count
    else:
        average_posts = 0

    print("")
    print("-------------Summary-----------------")
    print(f"Users saved: {qualified_users_count} at {args.output_file}")
    print(f"Summary for control: {args.summary_file}")
    print(f"Average # of posts per qualified user: {average_posts:.2f}")
    print(f"Users with less than {non_mh_threshold} posts: {non_qualified_users_count}")
    print("------------------------------")
    print('')



if __name__ == '__main__':
    main()
