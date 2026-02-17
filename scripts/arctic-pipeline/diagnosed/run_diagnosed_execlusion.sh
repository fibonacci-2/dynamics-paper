#!/bin/bash

# A) No posts made in MH subreddits
# B) No mention of any MH realated term
# runs execlusion against A) and B) conditions and saves output in condition/final
# Example run: 
#     bash run_diagnosed_execlusion.sh adhd_output 20
#     runs execlusion with 20 minimum posts per user

# Check if the user provided the required arguments
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <INPUT_FOLDER>"
    exit 1
fi

# Input file path provided by the user
INPUT_FOLDER=$1
# Output file path provided by the user
FINAL_OUTPUT="${INPUT_FOLDER}/diagnosed/data-diagnosed.final.json"
FINAL_SUMMARY="${INPUT_FOLDER}/diagnosed/non_mh_subreddits_summary.json"

# Threshold provided by the user

# Hardcoded paths to the Python scripts
EXECLUDE_MH_SUBREDDITS="exclude_mh_subreddits.py"
EXECLUDE_MH_MENTIONS="exclude_mh_mentions.py"
FORMATTER="../preprocessing/format_clean_diagnosed.py"


# Intermediate file
TEMP_OUTPUT="${INPUT_FOLDER}/diagnosed/exclusion.temp.json"

# Execute the first Python script
echo ""
echo "A) Execluding submissions made in MH subreddits..."
python3 "$EXECLUDE_MH_SUBREDDITS" "${INPUT_FOLDER}/diagnosed/diagnosed-users-all-submissions.json" "$TEMP_OUTPUT" 
rm "${INPUT_FOLDER}/diagnosed/diagnosed-users-all-submissions.json"
echo "Done excluding mh submissions..."
echo ""

# Check if the first script executed successfully
if [ $? -eq 0 ]; then
    # Execute the second Python script
    echo "B) Excluding submissions with MH terms..."
    python3 "$EXECLUDE_MH_MENTIONS" "$TEMP_OUTPUT" "$FINAL_OUTPUT" "$FINAL_SUMMARY"
    rm $TEMP_OUTPUT
    echo "Done excluding submissions with  mental health terms."
    echo ""
    echo "Generating CYMO format..."
    echo ""
    python3 $FORMATTER "${INPUT_FOLDER:0}/diagnosed/data-diagnosed.final.json" "${INPUT_FOLDER}/diagnosed/diagnosed-data.cymo.csv"
    echo "Done generating cymo format"
else
    echo "Error: The first Python script did not execute successfully."
    exit 1
fi
