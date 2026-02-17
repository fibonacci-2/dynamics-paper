import json
import argparse

# applies the first exclusion criteria: removing submissions that have been made in a mental health related subreddit.
# outputs two files: non mental health submissions (), summary of data filtered


def load_subreddits(file_path):
    with open(file_path, 'r') as file:
        return [line.strip().lower() for line in file.readlines()]


def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


def filter_non_mental_health_submissions(input_file, output_file, subreddits_file):
    subreddits = load_subreddits(subreddits_file)
    user_submissions = load_json(input_file)
    non_mental_health_users = []

    for user in user_submissions:
        non_mental_health_posts = [
            post for post in user['posts'] if post.get('subreddit') and post['subreddit'].lower() not in subreddits
        ]
        non_mental_health_subreddits = {
            post['subreddit'] for post in non_mental_health_posts if post.get('subreddit')}

        if non_mental_health_posts:
            non_mental_health_users.append(
                {'username': user['username'], 'posts': non_mental_health_posts, 'post_count': len(non_mental_health_posts)})

    # Save non-mental health posts to the output file
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(non_mental_health_users, file, indent=4)


    print(f"Saved {len(non_mental_health_users)} users with non-mental health posts to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Filter and save non-mental health Reddit posts.')
    parser.add_argument('input_file', type=str,
                        help='Path to the input JSON file containing user submissions')
    parser.add_argument('output_file', type=str,
                        help='Path to save the non-mental health posts JSON file')
  
    args = parser.parse_args()

    # Hardcoded path to the subreddits text file
    subreddits_file = '../../../resources/mh_subreddits.txt'

    filter_non_mental_health_submissions(
        args.input_file, args.output_file, subreddits_file)


if __name__ == '__main__':
    main()
