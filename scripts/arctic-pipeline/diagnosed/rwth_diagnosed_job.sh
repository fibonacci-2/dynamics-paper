#!/usr/bin/zsh

### Maximum runtime
#SBATCH --time=72:00:00
#SBATCH --partition=c23ms

### Ask for 8 cpus (tasks in Slurm terms) in the same node
#SBATCH --ntasks=1         ### 8*1 = 8 CPUS
#SBATCH --cpus-per-task=24  ### 8*1 = 8 CPUS
#SBATCH --nodes=1

#ask for 20GB within each node (1)
#SBATCH --mem=128GB

### Name the job
#SBATCH --job-name=ocd-d

### Declare an output STDOUT/STDERR file
#SBATCH --output=/home/qo750324/saad/logs/ocd_diagnosed_output.%J.txt

### Beginning of yourograms
### Note: The OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK envvar is set automatically by us
###       for you as a convenience. Expert users can modify it:
### OMP_NUM_THREADS=

echo "started resuming adhd diagnosis"

bash generate_diagnosed.sh /work/qo750324/arctic/ocd/combined ocd 20

#bash generate_control.sh ../../../data/bipolar_output

echo "after the job"
