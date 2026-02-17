import json
import csv
import argparse
import re

def daniel_cleaning(text):
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

def convert_json_to_csv(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)

    unique_texts = set()
    duplicate_count = 0

    with open(output_file, 'w', newline='', encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file)
        # Write the header
        csv_writer.writerow(['TID', 'text'])

        for user_data in data:
            username = user_data['username']
            for post in user_data['posts']:
                tid = f"1_{username}_{post['id']}"
                text = post.get('selftext', '')
                cleaned_text = daniel_cleaning(text)
                if cleaned_text in unique_texts:
                    duplicate_count += 1
                    continue
                unique_texts.add(cleaned_text)
                csv_writer.writerow([tid, cleaned_text])

    print(f"Data has been successfully converted to {output_file}")
    print(f"# of duplicated posts: {duplicate_count}")
    if len(unique_texts) > 0:
        print(f"Ratio of duplicate posts: {duplicate_count/len(unique_texts)}")

def main():
    parser = argparse.ArgumentParser(description='Convert JSON file to CSV with specified format and perform text cleaning.')
    parser.add_argument('input_file', type=str, help='Path to the input JSON file')
    parser.add_argument('output_file', type=str, help='Path to save the output CSV file')

    args = parser.parse_args()

    convert_json_to_csv(args.input_file, args.output_file)

if __name__ == '__main__':
    main()
