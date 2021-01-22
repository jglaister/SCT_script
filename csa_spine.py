import spinalcordtoolbox
from spinalcordtoolbox.deepseg_sc import core as deepseg_sc
from msct_register import Paramreg, ParamregMultiStep, register_wrapper
from spinalcordtoolbox.image import Image
import os, os.path, glob
import subprocess
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import nibabel as nib
import numpy as np
from multiprocessing import Pool

def process_csa_spine(PSIR_file):
    split_path = os.path.split(PSIR_file)
    #print(split_path[1])
    subj_id = split_path[1].split('_')[0]
    scan_id = split_path[1].split('_')[1]
    output_folder = os.path.join(split_path[0], 'PSIR', subj_id + '_' + scan_id)
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Segment spine
    print("Starting segmenting spine " + split_path[1])
    command = ["sct_propseg",
               "-i", PSIR_file,
               "-c", "t1",
               "-ofolder", output_folder
               ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
    #print(result.stdout)
    #print(result.stderr)
    spine_seg = os.path.join(output_folder, subj_id + '_' + scan_id + '_SPINE_PSIR_seg.nii.gz')

    # Create registration mask
    #print("Creating registration mask")
    command = ["sct_label_vertebrae",
               "-i", PSIR_file,
               "-s",spine_seg,
               "-c","t1",
               "-ofolder",output_folder
               ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
    #print(result.stdout)
    #print(result.stderr)


    vert_seg = os.path.join(output_folder, subj_id + '_' + scan_id + '_SPINE_PSIR_seg_labeled.nii.gz')

    # Register MT_OFF image
    #print("Registering MT OFF")
    output_csv = os.path.join(output_folder, subj_id + '_' + scan_id + '_MTR_vert.csv')
    command = [
        "sct_process_segmentation",
        "-i", spine_seg,
        "-perlevel", "1",
        "-vert", "2:7",
        "-vertfile", vert_seg,
        "-o", output_csv,
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
    #print(result.stdout)
    #print(result.stderr)

    #print("Computing MTR")
    output_csv = os.path.join(output_folder, subj_id + '_' + scan_id + '_MTR_perslice.csv')
    command = [
        "sct_process_segmentation",
        "-i", spine_seg,
        "-perslice", "1",
        "-vert", "2:7",
        "-vertfile", vert_seg,
        "-o", output_csv,
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
    #print(result.stdout)
    #print(result.stderr)

    #print("Locating c3c4")
    output_csv = os.path.join(output_folder, subj_id + '_' + scan_id + '_MTR_avg.csv')
    command = [
        "sct_process_segmentation",
        "-i", spine_seg,
        "-vert", "2:7",
        "-vertfile", vert_seg,
        "-o", output_csv,
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
    #print(result.stdout)
    #print(result.stderr)

    print("Done " + split_path[1])

if __name__ == '__main__':
    
    os.environ["PATH"] += os.pathsep + os.path.join('/home/j/jiwonoh/jglaist1/.virtualenvs/smhms/bin/')

    path = "/home/j/jiwonoh/jglaist1/scratch/data/SpinalCord/*_PSIR.nii.gz"
    PSIR_files = sorted(glob.glob(path))

    
    num_workers = 40
    pool = Pool(processes=num_workers)
    pool.map(process_csa_spine, PSIR_files[4:])
    pool.close()
        