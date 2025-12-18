#!/bin/bash
#SBATCH --account=bphl-umbrella
#SBATCH --qos=bphl-umbrella
#SBATCH --job-name=hav
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
#SBATCH --mem=400gb
#SBATCH --output=hav.%j.out
#SBATCH --error=hav.%j.err
#SBATCH --time=12:00:00


module load apptainer
module load nextflow

APPTAINER_CACHEDIR=./
export APPTAINER_CACHEDIR

NXF_SINGULARITY_CACHEDIR=./
export NXF_SINGULARITY_CACHEDIR

##### run HAV pipeline
echo "run HAV pipeline"
nextflow run hav.nf -params-file params_hav.yaml
sort ./output/*/report.txt | uniq > ./output/sum_report.txt
sed -i '/sampleID\tspecies|tax_ID|percent(%)|number/d' ./output/sum_report.txt
sed -i '1i sampleID\tspecies|tax_ID|percent(%)|number\treference\tstart\tend\tnum_raw_reads\tnum_clean_reads\tnum_mapped_reads\tpercent_mapped_clean_reads\tcov_bases_mapped\tpercent_genome_cov_map\tmean_depth\tmean_base_qual\tmean_map_qual' ./output/sum_report.txt

##### The most dominant genotype is selected in each sample, and then a SNP-based phylogenetic tree is constructed
mkdir ./output/extract
#python ./braken_phy_hav.py
python ./braken_phy_hav_VPB.py

#### move tree relevant files to the folder tree
mkdir ./output/trees
mv ./output/extract/SNPs* ./output/trees
mv ./output/extract/pairwise_matrix* ./output/trees
mv ./output/extract/mafft_* ./output/trees

mv ./*.out ./output
mv ./*err ./output
dt=$(date "+%Y%m%d%H%M%S")
mv ./output ./output-$dt
rm -r ./work

# ###### test commands of genotype tree
# python test_genotype_tree.py