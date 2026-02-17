import pandas as pd
import argparse

def split_csv(input_file, num_sections):
    # Load the CSV file
    df = pd.read_csv(input_file)
    
    # Calculate the number of rows per section
    total_rows = len(df)
    rows_per_section = total_rows // num_sections + (1 if total_rows % num_sections != 0 
else 0)
    
    # Prefix for output files
    output_prefix = 'split_data'
    
    # Split and save each section
    for i in range(num_sections):
        # Calculate start and end rows for the current section
        start_row = i * rows_per_section
        end_row = min(start_row + rows_per_section, total_rows)
        
        # Slice the DataFrame to get the current section
        section_df = df[start_row:end_row]
        
        # Define output file name
        output_file = f"{output_prefix}_section_{i+1}.csv"
        
        # Save the section to a new CSV file
        section_df.to_csv(output_file, index=False)
        print(f"Saved section {i+1} to {output_file}")

# Command-line argument parsing
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Split a large CSV file into smaller sections.')
    parser.add_argument('input_file', type=str, help='Path to the input CSV file')
    parser.add_argument('--sections', type=int, required=True, help='Number of sections to split the CSV into')
    
    args = parser.parse_args()
    
    split_csv(args.input_file, args.sections)

