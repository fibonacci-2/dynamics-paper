#!/bin/bash

# takes arctic downloaded condition file and runs it thorugh the diagnosis logic, 
# giving all submissions diagnosed users made, ready for mental health content execlusion 
# Example ruN
#      bash run_condition_diagnosis.sh ~/Downloads/r_ADHD_posts.jsonl ADHD 20
#      runs diagnosis on the given jsonl file with minimum 20 posts with the condition named ADHD

# Check if the user provided the required arguments
if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <path_to_input_file>  <condition_name> <minimum posts for user> [<all_user_submissions_output_file>]"
    exit 1
fi

# Input file path provided by the user
INPUT_FILE="$1"

# Condition name provided by the user
CONDITION_NAME="$2"

# Optional parameters

# Hardcoded paths to the Python scripts
CLEANING_SCRIPT="initial_cleaning.py"
DIAGNOSIS_SCRIPT="separate_diagnosed_users.py"
FETCH_SUBMISSIONS_SCRIPT="fetch_all_user_submissions.py"
FINAL_CLEANING_SCRIPT="final_cleaning.py"

# Create the condition folder
CONDITION_FOLDER="../../../data/${CONDITION_NAME}_output"
mkdir -p "$CONDITION_FOLDER"
mkdir -p "${CONDITION_FOLDER}/diagnosed"
LOG="${CONDITION_FOLDER}/diagnosed.log.txt"
# Intermediate files
CLEANED_OUTPUT_FILE="${CONDITION_FOLDER}/diagnosed/cleaned-pre-diagnosis-data.json"
DIAGNOSED_AUTHORS_FILE="${CONDITION_FOLDER}/diagnosed/diagnosed-usernames.json"
FINAL_CLEANED_SUBMISSIONS_FILE="${CONDITION_FOLDER}/diagnosed/diagnosed-users-all-submissions.json"
ALL_USER_SUBMISSIONS_OUTPUT_FILE="${CONDITION_FOLDER}/${5:-all_user_submissions.json}"
{
# Execute the first Python script with the input and output file paths
echo "Generating diagnosed data..."
echo ""
python3 "$CLEANING_SCRIPT" "$INPUT_FILE" "$CLEANED_OUTPUT_FILE"
echo ""

# Check if the first script executed successfully
if [ $? -eq 0 ]; then
    # Execute the second Python script with the cleaned output file and threshold
    echo "Diagnosing ${CONDITION_NAME} users....."
    python3 "$DIAGNOSIS_SCRIPT" "$CLEANED_OUTPUT_FILE" "$DIAGNOSED_AUTHORS_FILE" "$CONDITION_NAME"
    echo "Done diagnosing users....."
    echo ""

    # Check if the second script executed successfully
    if [ $? -eq 0 ]; then
        # Execute the third Python script to fetch all user submissions
        echo "Fetching all user submissions for diagnosed users....."
        echo ""
        python3 "$FETCH_SUBMISSIONS_SCRIPT" "$DIAGNOSED_AUTHORS_FILE" --output_file "$ALL_USER_SUBMISSIONS_OUTPUT_FILE" 
        echo ""

        # Check if the third script executed successfully
        if [ $? -eq 0 ]; then
            # Execute the final cleaning script on the fetched submissions
            echo "Cleaning downloaded data...."
            python3 "$FINAL_CLEANING_SCRIPT" "$ALL_USER_SUBMISSIONS_OUTPUT_FILE" "$FINAL_CLEANED_SUBMISSIONS_FILE"
            # rm $CLEANED_OUTPUT_FILE
            echo "Done fetching submissions..... YAI!!!!!" 
            echo "--------------------------------"
            echo ""
            echo ""
            echo "Applying execlusion patterns..."
            echo ""
            bash "run_diagnosed_execlusion.sh" $CONDITION_FOLDER
            echo ""
        else
            echo "Error: The fetch submissions script did not execute successfully."
            exit 1
        fi
    else
        echo "Error: The diagnosis script did not execute successfully."
        exit 1
    fi
else
    echo "Error: The cleaning script did not execute successfully."
    exit 1
fi
} &> "$LOG"
