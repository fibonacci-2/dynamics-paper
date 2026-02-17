import pandas as pd

csv_file2 = '/Users/macbookpro/Desktop/data/annotated/diagnosed_p1.liwc.csv' # Replace with the actual path of the second CSV file
csv_file1 = '/Users/macbookpro/Desktop/data/annotated/diagnosed_p2.liwc.csv' # Replace with the actual path of the second CSV file

# Read the CSV files into DataFrames
df1 = pd.read_csv(csv_file1)
df2 = pd.read_csv(csv_file2)

# Combine the DataFrames
combined_df = pd.concat([df1, df2], ignore_index=True)

# Save the combined DataFrame to a new CSV file
combined_df.to_csv('/Users/macbookpro/Desktop/data/annotated/mindset_diagnosed.liwc.csv', index=False)

print("Combined file saved as 'combined_file.csv'")

