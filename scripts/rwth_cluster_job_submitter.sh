#!/usr/bin/zsh

### Maximum runtime
SBATCH --time=09:15:00

### Ask for 8 cpus (tasks in Slurm terms) in the same node
SBATCH --ntasks=1         ### 8*1 = 8 CPUS
SBATCH --cpus-per-task=8  ### 8*1 = 8 CPUS
SBATCH --nodes=1

#ask for 20GB within each node (1)
SBATCH --mem=64GB

### Name the job
SBATCH --job-name=anxiety-diagnosis

### Declare an output STDOUT/STDERR file
SBATCH --output=/home/qo750324/saad/logs/output.%J.txt

### Beginning of your programs
### Note: The OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK envvar is set automatically by us
###       for you as a convenience. Expert users can modify it:
### OMP_NUM_THREADS=

echo 6969

#bash /home/qo750324/saad/main-project/reddit/scripts/arctic-pipeline/diagnosed/generate_diagnosed.sh home/qo750324/saad/arctic/anxiety/combined anxiety 
bash /home/qo750324/saad/main-project/reddit/scripts/arctic-pipeline/control/generate_control.sh home/qo750324/saad/main-project/reddit/data/ptsd_otuput
