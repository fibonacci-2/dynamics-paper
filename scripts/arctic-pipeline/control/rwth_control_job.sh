#!/usr/bin/zsh

#SBATCH --time=6-15:00:00
#SBATCH --partition=c23ms
#SBATCH --ntasks=1         ### 8*1 = 8 CPUS
#SBATCH --cpus-per-task=12  ### 8*1 = 8 CPUS
#SBATCH --nodes=1

#SBATCH --mem=32GB

#SBATCH --job-name=dep-4

#SBATCH --output=/home/qo750324/saad/logs/depression_sections_4_control_output.%J.txt


echo "before the job"

bash generate_control.sh ../../../data/depression_output/section_4_output

echo "after the job"
