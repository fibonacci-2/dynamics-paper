import json
import re
import argparse



# Function to check if selftext is valid
def is_valid_selftext(selftext):
    invalid_patterns = [
        r'^\[deleted\]$',        # Exactly "[deleted]"
        r'^\[removed\]$',        # Exactly "[removed]"
        r'\[deleted\]',          # Contains "[deleted]"
        r'\[removed\]',          # Contains "[removed]"
        r'^\s*$',                # Empty or whitespace-only
        r'\[View Poll\]\(https://www.reddit.com/poll/.*\)',  # Poll link pattern
    ]
    for pattern in invalid_patterns:
        if re.search(re.escape(pattern), selftext, re.IGNORECASE):
            return False

    # Check if there is at least one sentence-ending punctuation mark
    if not re.search(r'[.!?]', selftext):
        return False

    # Check if the sentence is too short (one or two words)
    sentences = re.split(r'[.!?]', selftext)
    for sentence in sentences:
        words = sentence.strip().split()
        if len(words) > 15:
            return True

    return False

# Function to filter and simplify posts
def filter_and_simplify_posts(input_file, output_file):
    # Define relevant properties to keep
    relevant_properties = ['id', 'title', 'selftext', 'author', 'created_utc', 'subreddit', 'score']

    simplified_user_submissions = []
    total_simplified_posts = 0
    total_length = 0

    # Load the JSON file
    with open(input_file, 'r', encoding='utf-8') as file:
        all_user_submissions = json.load(file)

    # Filter and simplify the posts
    for user_data in all_user_submissions:
        simplified_posts = []
        for post in user_data['posts']:
            selftext = post.get('selftext', '')
            if is_valid_selftext(selftext):
                simplified_post = {prop: post[prop] for prop in relevant_properties if prop in post}
                simplified_posts.append(simplified_post)
                total_length += len(selftext)
                total_simplified_posts += 1

        if simplified_posts:
            simplified_user_data = {
                'username': user_data['username'],
                'posts': simplified_posts
            }
            simplified_user_submissions.append(simplified_user_data)

    # Save the simplified posts to a new JSON file
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(simplified_user_submissions, file, indent=4)

    if total_simplified_posts:
        average_length = total_length / total_simplified_posts
    else:
        average_length = 0

    print("")
    print("-------------Summary-----------------")
    print(f"Average diagnosed post length: {average_length:.2f} characters")

def main():
    parser = argparse.ArgumentParser(
        description='Filter and simplify user submissions JSON file for NLP projects.')
    parser.add_argument('input_file', type=str,
                        help='Path to the input JSON file containing all user submissions')
    parser.add_argument('output_file', type=str,
                        help='Path to save the simplified JSON file')

    args = parser.parse_args()

    filter_and_simplify_posts(args.input_file, args.output_file)

if __name__ == '__main__':
    main()
