import os
import json
import argparse

def process_files(input_folder):
    comments_output_path = os.path.join(input_folder, 'comments.jsonl')
    posts_output_path = os.path.join(input_folder, 'posts.jsonl')

    with open(comments_output_path, 'w') as comments_outfile, open(posts_output_path, 'w') as posts_outfile:
        for filename in os.listdir(input_folder):
            if filename.endswith('_comments.jsonl'):
                with open(os.path.join(input_folder, filename), 'r') as infile:
                    for line in infile:
                        comments_outfile.write(line)
            elif filename.endswith('_posts.jsonl'):
                with open(os.path.join(input_folder, filename), 'r') as infile:
                    for line in infile:
                        posts_outfile.write(line)
            print(f'processed file {filename}')
    
    print(f"Combined comments written to: {comments_output_path}")
    print(f"Combined posts written to: {posts_output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Combine JSONL files for comments and posts.')
    parser.add_argument('input_folder', type=str, help='The input folder containing the JSONL files.')
    args = parser.parse_args()

    process_files(args.input_folder)
