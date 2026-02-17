import json
import argparse
import os

def split_json_file(input_file, output_dir, sections=2):
    # Read the JSON file
    with open(input_file, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # Determine the size of each section
    total_length = len(data)
    section_size = total_length // sections
    
    # Split the data into sections
    for i in range(sections):
        start_index = i * section_size
        end_index = (i + 1) * section_size if i < sections - 1 else total_length
        section_data = data[start_index:end_index]
        
        # Define the section directory path
        section_dir = os.path.join(output_dir, f'section_{i+1}_output', 'diagnosed')
        os.makedirs(section_dir, exist_ok=True)
        
        # Define the output file path
        output_file = os.path.join(section_dir, 'non_mh_subreddits_summary.json')
        
        # Write the section to a new JSON file
        with open(output_file, 'w', encoding='utf-8') as outfile:
            json.dump(section_data, outfile, indent=4)
        
        print(f"Section {i+1} saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Split a JSON file into sections while maintaining order.')
    parser.add_argument('input_file', type=str, help='Path to the input JSON file')
    parser.add_argument('output_dir', type=str, help='Directory to save the output JSON files')
    parser.add_argument('--sections', type=int, default=2, help='Number of sections to split the file into (default: 2)')

    args = parser.parse_args()
    
    # Split the JSON file
    split_json_file(args.input_file, args.output_dir, args.sections)
