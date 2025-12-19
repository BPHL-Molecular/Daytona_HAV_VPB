import sys
import os
import argparse
current_dir = os.getcwd()

### extract HAV reads and generate consensus sequence
with open("./output/sum_report.txt", 'r') as kreport:
        lines = kreport.readlines()
        for l in lines[1:]:
            l_parse = l.lstrip().rstrip().split("\t")
            sampleID = l_parse[0].lstrip()
            species_group = l_parse[1].lstrip().rstrip().split(",")
            #species_items = species_group[1].lstrip().rstrip().split("|")
            species_items = species_group[0].lstrip().rstrip().split("|")
            tax = species_items[0].lstrip()
            taxID = species_items[1].lstrip()

            substring = "Hepatovirus A"
            if(substring.lower() in tax.lower()):
                os.system(f"python ./extract_kraken_reads.py -k {current_dir}/output/{sampleID}/kraken_out/{sampleID}_kraken.out -s {current_dir}/fastqs/hav/{sampleID}_1.fastq.gz -s2 {current_dir}/fastqs/hav/{sampleID}_2.fastq.gz -o {current_dir}/output/extract/{sampleID}_{taxID}_1.fq -o2 {current_dir}/output/extract/{sampleID}_{taxID}_2.fq -t {taxID}")
                os.system(f"singularity exec docker://staphb/bwa:0.7.17 bwa mem {current_dir}/reference/hav/NC_001489.fasta {current_dir}/output/extract/{sampleID}_{taxID}_1.fq {current_dir}/output/extract/{sampleID}_{taxID}_2.fq > {current_dir}/output/extract/{sampleID}_{taxID}_aln.sam")
                os.system(f"singularity exec docker://staphb/samtools:1.12 samtools view -F 4 -u -h -bo {current_dir}/output/extract/{sampleID}_{taxID}_aln.bam {current_dir}/output/extract/{sampleID}_{taxID}_aln.sam")
                os.system(f"singularity exec docker://staphb/samtools:1.12 samtools sort -n -o {current_dir}/output/extract/{sampleID}_{taxID}.namesorted.bam {current_dir}/output/extract/{sampleID}_{taxID}_aln.bam")
                os.system(f"singularity exec docker://staphb/samtools:1.12 samtools fixmate -m {current_dir}/output/extract/{sampleID}_{taxID}.namesorted.bam {current_dir}/output/extract/{sampleID}_{taxID}.fixmate.bam")
                os.system(f"singularity exec docker://staphb/samtools:1.12 samtools sort -o {current_dir}/output/extract/{sampleID}_{taxID}.positionsort.bam {current_dir}/output/extract/{sampleID}_{taxID}.fixmate.bam")
                #os.system(f"singularity exec docker://staphb/samtools:1.12 samtools markdup {current_dir}/output/extract/{sampleID}_{taxID}.positionsort.bam {current_dir}/output/extract/{sampleID}_{taxID}.markdup.bam")
                os.system(f"singularity exec docker://staphb/samtools:1.12 samtools markdup -r {current_dir}/output/extract/{sampleID}_{taxID}.positionsort.bam {current_dir}/output/extract/{sampleID}_{taxID}.dedup.bam")
                os.system(f"singularity exec docker://staphb/samtools:1.12 samtools sort -o {current_dir}/output/extract/{sampleID}_{taxID}.sorted.bam {current_dir}/output/extract/{sampleID}_{taxID}.dedup.bam")
                os.system(f"singularity exec docker://staphb/samtools:1.12 samtools mpileup -A -B -d 8000 --reference {current_dir}/reference/hav/NC_001489.fasta -Q 0 {current_dir}/output/extract/{sampleID}_{taxID}.sorted.bam | singularity exec docker://staphb/ivar:latest ivar consensus -t 0 -m 10 -n N -p {current_dir}/output/extract/{sampleID}_{taxID}.consensus")
            
            else:
                print(f"No any Hepatovirus A virus is found in {sampleID}, based on the kraken output of {sampleID}.")
                print(f"Please check the issue from {sampleID}.")
                break
                
os.system(f"cat {current_dir}/output/extract/*.consensus.fa > {current_dir}/output/extract/sum_consensus.fa")
os.system(f"sed -i 's/>Consensus_/>/g; s/\.consensus_threshold_.*//g' {current_dir}/output/extract/sum_consensus.fa")
#os.system(f"mafft {current_dir}/output/extract/sum_consensus.fa > {current_dir}/output/extract/mafft_msa")


### analyses test data (genotype, tree, mutations, etc.) by nextclade with its HAV reference dataset 
os.system(f"nextclade run --include-reference --input-dataset={current_dir}/reference/ref_nextclade --input-ref={current_dir}/reference/ref_nextclade/reference.fasta --output-all={current_dir}/output/nextclade {current_dir}/output/extract/sum_consensus.fa")

### visualize tree
os.system(f"singularity exec docker://staphb/phytreeviz:latest phytreeviz -i {current_dir}/output/nextclade/nextclade.nwk -o {current_dir}/output/tree_with_reference.svg --show_confidence")
os.system(f"singularity exec docker://staphb/phytreeviz:latest phytreeviz -i {current_dir}/output/nextclade/nextclade.nwk -o {current_dir}/output/tree_with_reference.pdf --show_confidence")