import pandas as pd
import argparse
import os

def merge_csv(file1, file2, output_file=None, balanced_output_file=None):
    # Read the CSV files into DataFrames
    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)
    print(df2.head())
    print(df1.head())

    # Concatenate the two DataFrames
    merged_df = pd.concat([df1, df2]).reset_index(drop=True)

    if output_file:
        # Save the merged DataFrame to a new CSV file if output file is provided
        merged_df.to_csv(output_file, index=False)
        print(f"Merged data saved to {output_file}")

    # Create a balanced dataset
    diagnosed_df = df1.copy()  # Assuming df1 is diagnosed
    control_df = df2.sample(n=len(diagnosed_df), random_state=42)  # Randomly sample controls equal to the number of diagnosed
    balanced_df = pd.concat([diagnosed_df, control_df]).reset_index(drop=True)

    if balanced_output_file:
        # Save the balanced DataFrame to a new CSV file if balanced output file is provided
        balanced_df.to_csv(balanced_output_file, index=False)
        print(f"Balanced data saved to {balanced_output_file}")
    else:
        # Print the first few rows of the balanced DataFrame
        print(balanced_df.head())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Merge two CSV files with the same headers.')
    parser.add_argument('condition_dir', type=str, help='Path to the condition directory containing CSV files')

    args = parser.parse_args()
    base_name = os.path.basename(args.condition_dir.strip('/'))
    extracted_part = base_name.split('_')[0]
    merge_csv(
        f'{args.condition_dir}/diagnosed/diagnosed-data.cymo.csv', 
        f'{args.condition_dir}/control/control-data.cymo.csv',
        f'{args.condition_dir}/{extracted_part}-combined.csv',
        f'{args.condition_dir}/{extracted_part}-balanced-combined.csv'
    )
