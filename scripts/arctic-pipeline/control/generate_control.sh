#!/bin/bash

# Takes conditiou_output/ folder of the generate_diagnosed.sh script
# and runs control generation and matching to each diagnosed user

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <INPUT_FOLDER> <threshold>"
    exit 1
fi

# Input file path provided by the user
INPUT_FOLDER=$1
# Output file path provided by the user
CONDITION_FOLDER="${INPUT_FOLDER}/control"
LOG="${INPUT_FOLDER}/control.log.txt"


# Hardcoded paths to the Python scripts
FIND_CANDIDATES="get_control_candidates.py"
MATCH_CONTROLS="match_controls.py"
CONTROL_FORMATTER="../preprocessing/format_clean_control.py"  # Replace with the actual name of your third script

# Intermediate file
TEMP_OUTPUT="${INPUT_FOLDER}/control/candidate-controls.temp.json"

{
# first find candidate controls from non mh subreddits
echo ""
echo "Finding control candidates..."
python3 "$FIND_CANDIDATES" "${INPUT_FOLDER}/diagnosed/non_mh_subreddits_summary.json" "$TEMP_OUTPUT" 
echo ""

# Check if the first script executed successfully
if [ $? -eq 0 ]; then
    # Execute the second Python script
    echo "Matching found controls..."
    python3 "$MATCH_CONTROLS" "$TEMP_OUTPUT" "$CONDITION_FOLDER"
    echo ""

    # Check if the second script executed successfully
    if [ $? -eq 0 ]; then
        # Execute the third Python script
        echo "Generating csv..."
        python3 "$CONTROL_FORMATTER" "${CONDITION_FOLDER}" "${CONDITION_FOLDER}/control-data.cymo.csv" # Modify the arguments as needed
        echo "Done gemerating csv and cleaning the file."
        echo ""
    else
        echo "Error: The second Python script did not execute successfully."
        exit 1
    fi
else
    echo "Error: The first Python script did not execute successfully."
    exit 1
fi
} &> "$LOG"