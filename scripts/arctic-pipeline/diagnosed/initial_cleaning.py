import json
import re
import argparse
import os

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

# Function to check if text is valid
def is_valid_text(text, text_with_add):
    invalid_patterns = [
        r'^\[deleted\]$',        # Exactly "[deleted]"
        r'^\[removed\]$',        # Exactly "[removed]"
        r'\[deleted\]',          # Contains "[deleted]"
        r'\[removed\]',          # Contains "[removed]"
        r'^\s*$',                # Empty or whitespace-only
        r'\[View Poll\]\(https://www.reddit.com/poll/.*\)',  # Poll link pattern
        r'https?://\S+',         # Contains a URL
        r'[^a-zA-Z0-9\s\.\'\!\?\,\;\-]'  # Non-English characters
    ]
    for pattern in invalid_patterns:
        if re.search(re.escape(pattern), text, re.IGNORECASE):
            return False

    # Check if there is at least one sentence-ending punctuation mark
    if not re.search(r'[.!?]', text):
        return False

    # ignore posts with add pattern
    if  " add " in text.lower() or " add. " in text.lower() or " add," in text.lower():
        text_with_add += 1
        return False
    
    # Check if the sentence is too short (one or two words)
    sentences = re.split(r'[.!?]', text)
    for sentence in sentences:
        words = sentence.strip().split()
        if len(words) > 2:
            return True

    return False

# Function to filter and simplify posts and comments
def filter_and_simplify(input_folder, output_file):
    # Define relevant properties to keep
    relevant_properties = ['id', 'title', 'selftext', 'author', 'created_utc', 'subreddit', 'score']
    comment_properties = ['id', 'selftext', 'author', 'created_utc', 'subreddit', 'score']

    simplified_submissions = []
    unique_texts = set()
    total_simplified_posts = 0
    total_length = 0
    duplicate_count = 0
    text_with_add = 0


    # Process posts
    posts_file = os.path.join(input_folder, 'posts.jsonl')
    if os.path.exists(posts_file):
        with open(posts_file, 'r', encoding='utf-8') as file:
            for line in file:
                post = json.loads(line.strip())
                selftext = post.get('selftext', '')
                author = post.get('author', '')
                if is_valid_text(selftext, text_with_add) and author != '[deleted]':
                    cleaned_text = preprocess_text(selftext)
                    if cleaned_text in unique_texts:
                        duplicate_count += 1
                        continue
                    unique_texts.add(cleaned_text)
                    simplified_post = {prop: post[prop] for prop in relevant_properties if prop in post}
                    simplified_post['selftext'] = cleaned_text  # Replace with cleaned text
                    simplified_submissions.append(simplified_post)
                    total_length += len(selftext)
                    total_simplified_posts += 1

    # Process comments
    comments_file = os.path.join(input_folder, 'comments.jsonl')
    if os.path.exists(comments_file):
        with open(comments_file, 'r', encoding='utf-8') as file:
            for line in file:
                comment = json.loads(line.strip())
                body = comment.get('body', '')
                author = comment.get('author', '')
                if is_valid_text(body, text_with_add) and author != '[deleted]':
                    cleaned_text = preprocess_text(body)
                    if cleaned_text in unique_texts:
                        duplicate_count += 1
                        continue
                    unique_texts.add(cleaned_text)
                    simplified_comment = {prop: comment[prop] for prop in comment_properties if prop in comment}
                    simplified_comment['selftext'] = cleaned_text  # Rename body to selftext and replace with cleaned text
                    simplified_submissions.append(simplified_comment)
                    total_length += len(body)
                    total_simplified_posts += 1

    # Save the simplified posts and comments to a new JSON file
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(simplified_submissions, file, indent=4)

    print(f"Valid posts and comments read: {total_simplified_posts}")
    print(f"Duplicated posts and comments: {duplicate_count}")
    print(f"Texts with add ignored: {text_with_add}")

def preprocess_text(text):
    # Lowercasing Text
    text = text.lower()
    
    # Removing Hyperlinks
    text = re.sub(r'https?://\S+', '', text)
    
    # Removing HTML Tags
    text = re.sub(r'<.*?>', '', text)
    
    # Removing User Mentions
    text = re.sub(r'@\w+', '', text)
    
    # Removing HTML Entities
    text = re.sub(r'&\w+;', ' ', text)
    
    # Processing Hashtags
    text = re.sub(r'#(\w+)', r'\1', text)
    
    # Preserving Certain Characters and Whitespace
    text = re.sub(r'[^a-zA-Z0-9\s\.\'\!\?\,\;\-]', ' ', text)
    
    # Normalizing Spaces and Punctuation
    text = re.sub(r'(?<=[.,!?])(?=[^\s])', r' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'(\.|\!|\?|\,|\;)\1+', r'\1', text)  # Deduplicate sentence-ending symbols
    text = re.sub(r'\.{3,}', '.', text)  # Replace consecutive ellipsis with a single full stop
    text = text.strip()
    text = re.sub(r'(?<=\w)([.,;])(?=\S)', r'\1 ', text)
    
    # Ensure post ends with a full stop if it doesn't end with a sentence-ending symbol
    if not re.search(r'[.!?]$', text):
        text += '.'
    
    return text

def main():
    parser = argparse.ArgumentParser(
        description='Filter and simplify user submissions JSON files for NLP projects.')
    parser.add_argument('input_folder', type=str,
                        help='Path to the input folder containing all user submissions')
    parser.add_argument('output_file', type=str,
                        help='Path to save the simplified JSON file')

    args = parser.parse_args()

    filter_and_simplify(args.input_folder, args.output_file)

if __name__ == '__main__':
    main()
