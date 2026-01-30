import sys
import os
import argparse
import logging
from datetime import datetime

# Set up logging configuration
current_dir = os.getcwd()
log_dir = os.path.join(current_dir, "output", "logs")
os.makedirs(log_dir, exist_ok=True)

# Create log filename with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"hav_pipeline_{timestamp}.log")

# Configure logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

logger.info("="*80)
logger.info("Starting HAV VPB Pipeline")
logger.info(f"Working directory: {current_dir}")
logger.info(f"Log file: {log_file}")
logger.info("="*80)

### extract HAV reads and generate consensus sequence
logger.info("Reading Kraken report file...")
report_file = "./output/sum_report.txt"

if not os.path.exists(report_file):
    logger.error(f"Report file not found: {report_file}")
    sys.exit(1)

logger.info(f"Report file found: {report_file}")

try:
    with open(report_file, 'r') as kreport:
        lines = kreport.readlines()
        logger.info(f"Total lines in report: {len(lines)}")
        
        samples_processed = 0
        samples_with_hav = 0
        
        for line_num, l in enumerate(lines[1:], start=2):
            logger.info(f"Processing line {line_num}...")
            
            l_parse = l.lstrip().rstrip().split("\t")
            sampleID = l_parse[0].lstrip()
            species_group = l_parse[1].lstrip().rstrip().split(",")
            species_items = species_group[0].lstrip().rstrip().split("|")
            tax = species_items[0].lstrip()
            taxID = species_items[1].lstrip()
            
            logger.info(f"Sample ID: {sampleID}")
            logger.info(f"Taxonomy: {tax}")
            logger.info(f"Tax ID: {taxID}")
            
            substring = "Hepatovirus A"
            if(substring.lower() in tax.lower()):
                samples_with_hav += 1
                logger.info(f"✓ Hepatovirus A detected in {sampleID}")
                
                # Step 1: Extract Kraken reads
                logger.info(f"Step 1: Extracting Kraken reads for {sampleID}...")
                cmd = f"python ./extract_kraken_reads.py -k {current_dir}/output/{sampleID}/kraken_out/{sampleID}_kraken.out -s {current_dir}/fastqs/hav/{sampleID}_1.fastq.gz -s2 {current_dir}/fastqs/hav/{sampleID}_2.fastq.gz -o {current_dir}/output/extract/{sampleID}_{taxID}_1.fq -o2 {current_dir}/output/extract/{sampleID}_{taxID}_2.fq -t {taxID}"
                logger.debug(f"Command: {cmd}")
                ret_code = os.system(cmd)
                if ret_code != 0:
                    logger.error(f"Failed to extract reads for {sampleID} (exit code: {ret_code})")
                else:
                    logger.info(f"✓ Successfully extracted reads for {sampleID}")
                
                # Step 2: BWA alignment
                logger.info(f"Step 2: Running BWA alignment for {sampleID}...")
                cmd = f"singularity exec docker://staphb/bwa:0.7.17 bwa mem {current_dir}/reference/hav/NC_001489.fasta {current_dir}/output/extract/{sampleID}_{taxID}_1.fq {current_dir}/output/extract/{sampleID}_{taxID}_2.fq > {current_dir}/output/extract/{sampleID}_{taxID}_aln.sam"
                logger.debug(f"Command: {cmd}")
                ret_code = os.system(cmd)
                if ret_code != 0:
                    logger.error(f"BWA alignment failed for {sampleID} (exit code: {ret_code})")
                else:
                    logger.info(f"✓ BWA alignment completed for {sampleID}")
                
                # Step 3: SAM to BAM conversion
                logger.info(f"Step 3: Converting SAM to BAM for {sampleID}...")
                cmd = f"singularity exec docker://staphb/samtools:1.12 samtools view -F 4 -u -h -bo {current_dir}/output/extract/{sampleID}_{taxID}_aln.bam {current_dir}/output/extract/{sampleID}_{taxID}_aln.sam"
                logger.debug(f"Command: {cmd}")
                ret_code = os.system(cmd)
                if ret_code != 0:
                    logger.error(f"SAM to BAM conversion failed for {sampleID} (exit code: {ret_code})")
                else:
                    logger.info(f"✓ SAM to BAM conversion completed for {sampleID}")
                
                # Step 4: Name sort
                logger.info(f"Step 4: Name sorting BAM for {sampleID}...")
                cmd = f"singularity exec docker://staphb/samtools:1.12 samtools sort -n -o {current_dir}/output/extract/{sampleID}_{taxID}.namesorted.bam {current_dir}/output/extract/{sampleID}_{taxID}_aln.bam"
                logger.debug(f"Command: {cmd}")
                ret_code = os.system(cmd)
                if ret_code != 0:
                    logger.error(f"Name sorting failed for {sampleID} (exit code: {ret_code})")
                else:
                    logger.info(f"✓ Name sorting completed for {sampleID}")
                
                # Step 5: Fixmate
                logger.info(f"Step 5: Running fixmate for {sampleID}...")
                cmd = f"singularity exec docker://staphb/samtools:1.12 samtools fixmate -m {current_dir}/output/extract/{sampleID}_{taxID}.namesorted.bam {current_dir}/output/extract/{sampleID}_{taxID}.fixmate.bam"
                logger.debug(f"Command: {cmd}")
                ret_code = os.system(cmd)
                if ret_code != 0:
                    logger.error(f"Fixmate failed for {sampleID} (exit code: {ret_code})")
                else:
                    logger.info(f"✓ Fixmate completed for {sampleID}")
                
                # Step 6: Position sort
                logger.info(f"Step 6: Position sorting BAM for {sampleID}...")
                cmd = f"singularity exec docker://staphb/samtools:1.12 samtools sort -o {current_dir}/output/extract/{sampleID}_{taxID}.positionsort.bam {current_dir}/output/extract/{sampleID}_{taxID}.fixmate.bam"
                logger.debug(f"Command: {cmd}")
                ret_code = os.system(cmd)
                if ret_code != 0:
                    logger.error(f"Position sorting failed for {sampleID} (exit code: {ret_code})")
                else:
                    logger.info(f"✓ Position sorting completed for {sampleID}")
                
                # Step 7: Mark duplicates and remove
                logger.info(f"Step 7: Marking and removing duplicates for {sampleID}...")
                cmd = f"singularity exec docker://staphb/samtools:1.12 samtools markdup -r {current_dir}/output/extract/{sampleID}_{taxID}.positionsort.bam {current_dir}/output/extract/{sampleID}_{taxID}.dedup.bam"
                logger.debug(f"Command: {cmd}")
                ret_code = os.system(cmd)
                if ret_code != 0:
                    logger.error(f"Duplicate removal failed for {sampleID} (exit code: {ret_code})")
                else:
                    logger.info(f"✓ Duplicate removal completed for {sampleID}")
                
                # Step 8: Final sort
                logger.info(f"Step 8: Final sorting for {sampleID}...")
                cmd = f"singularity exec docker://staphb/samtools:1.12 samtools sort -o {current_dir}/output/extract/{sampleID}_{taxID}.sorted.bam {current_dir}/output/extract/{sampleID}_{taxID}.dedup.bam"
                logger.debug(f"Command: {cmd}")
                ret_code = os.system(cmd)
                if ret_code != 0:
                    logger.error(f"Final sorting failed for {sampleID} (exit code: {ret_code})")
                else:
                    logger.info(f"✓ Final sorting completed for {sampleID}")
                
                # Step 9: Generate consensus sequence
                logger.info(f"Step 9: Generating consensus sequence for {sampleID}...")
                cmd = f"singularity exec docker://staphb/samtools:1.12 samtools mpileup -A -B -d 8000 --reference {current_dir}/reference/hav/NC_001489.fasta -Q 0 {current_dir}/output/extract/{sampleID}_{taxID}.sorted.bam | singularity exec docker://staphb/ivar:latest ivar consensus -t 0 -m 10 -n N -p {current_dir}/output/extract/{sampleID}_{taxID}.consensus"
                logger.debug(f"Command: {cmd}")
                ret_code = os.system(cmd)
                if ret_code != 0:
                    logger.error(f"Consensus generation failed for {sampleID} (exit code: {ret_code})")
                else:
                    logger.info(f"✓ Consensus generation completed for {sampleID}")
                
                logger.info(f"✓✓✓ Sample {sampleID} processing complete ✓✓✓")
                samples_processed += 1
            
            else:
                logger.warning(f"✗ No Hepatovirus A virus found in {sampleID}")
                logger.warning(f"Detected taxonomy: {tax}")
                logger.warning(f"Please check the issue with {sampleID}")
                break
        
        logger.info("="*80)
        logger.info(f"Summary: Processed {samples_processed} samples with HAV out of {len(lines)-1} total samples")
        logger.info("="*80)
        
except Exception as e:
    logger.error(f"Error processing report file: {str(e)}", exc_info=True)
    sys.exit(1)

# Concatenate consensus sequences
logger.info("Concatenating consensus sequences...")
cmd = f"cat {current_dir}/output/extract/*.consensus.fa > {current_dir}/output/extract/sum_consensus.fa"
logger.debug(f"Command: {cmd}")
ret_code = os.system(cmd)
if ret_code != 0:
    logger.error(f"Failed to concatenate consensus sequences (exit code: {ret_code})")
else:
    logger.info("✓ Consensus sequences concatenated")

# Clean up sequence headers
logger.info("Cleaning up sequence headers...")
cmd = f"sed -i 's/>Consensus_/>/g; s/\\.consensus_threshold_.*//g' {current_dir}/output/extract/sum_consensus.fa"
logger.debug(f"Command: {cmd}")
ret_code = os.system(cmd)
if ret_code != 0:
    logger.error(f"Failed to clean sequence headers (exit code: {ret_code})")
else:
    logger.info("✓ Sequence headers cleaned")

### analyses test data (genotype, tree, mutations, etc.) by nextclade with its HAV reference dataset
logger.info("Running Nextclade analysis...")
cmd = f"singularity exec docker://nextstrain/nextclade:3.18.1 nextclade run --include-reference --input-dataset={current_dir}/reference/ref_nextclade --input-ref={current_dir}/reference/ref_nextclade/reference.fasta --output-all={current_dir}/output/nextclade {current_dir}/output/extract/sum_consensus.fa"
logger.debug(f"Command: {cmd}")
ret_code = os.system(cmd)
if ret_code != 0:
    logger.error(f"Nextclade analysis failed (exit code: {ret_code})")
else:
    logger.info("✓ Nextclade analysis completed")

### visualize tree
logger.info("Generating phylogenetic tree visualizations...")

# SVG format
logger.info("Creating SVG tree visualization...")
cmd = f"singularity exec docker://staphb/phytreeviz:latest phytreeviz -i {current_dir}/output/nextclade/nextclade.nwk -o {current_dir}/output/tree_with_reference.svg --show_confidence"
logger.debug(f"Command: {cmd}")
ret_code = os.system(cmd)
if ret_code != 0:
    logger.error(f"SVG tree visualization failed (exit code: {ret_code})")
else:
    logger.info("✓ SVG tree visualization created")

# PDF format
logger.info("Creating PDF tree visualization...")
cmd = f"singularity exec docker://staphb/phytreeviz:latest phytreeviz -i {current_dir}/output/nextclade/nextclade.nwk -o {current_dir}/output/tree_with_reference.pdf --show_confidence"
logger.debug(f"Command: {cmd}")
ret_code = os.system(cmd)
if ret_code != 0:
    logger.error(f"PDF tree visualization failed (exit code: {ret_code})")
else:
    logger.info("✓ PDF tree visualization created")

logger.info("="*80)
logger.info("HAV VPB Pipeline completed successfully!")
logger.info(f"Full log saved to: {log_file}")
logger.info("="*80)
