#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <folder>"
    exit 1
fi

folder=$1
counter=1

# Iterate over each file in the specified directory in order
for file in $(ls "$folder"/matched_control_batch_*.json | sort -V); do
    count=$(grep '"username"' "$file" | wc -l)
    echo "--$counter > $count"
    ((counter++))
done

