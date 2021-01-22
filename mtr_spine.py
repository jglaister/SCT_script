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

def process_mtr_spine(MT_file):
    # Find MT_OFF image and create output directory
        split_path = os.path.split(MT_file)
        #print(split_path[1])
        subj_id = split_path[1].split('_')[0]
        scan_id = split_path[1].split('_')[1]
        MT_off_file = os.path.join(split_path[0], subj_id + '_' + scan_id + '_SPINE_MT_OFF.nii.gz')
        output_folder = os.path.join(split_path[0], 'MT', subj_id + '_' + scan_id)
        if os.path.exists(MT_off_file):
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)

            # Segment spine
            print("Starting segmenting spine " + split_path[1])
            command = ["sct_deepseg_sc",
                       "-i", MT_file,
                       "-c", "t2",
                       "-o", output_folder
                       ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
            # print(result.stdout)
            # print(result.stderr)
            spine_seg = os.path.join(output_folder, subj_id + '_' + scan_id + '_SPINE_MT_seg.nii.gz')

            # Create registration mask
            #print("Creating registration mask")
            reg_mask = os.path.join(output_folder, subj_id + '_' + scan_id + '_SPINE_MT_regmask.nii.gz')
            command = ["sct_create_mask",
                       "-i", MT_file,
                       "-p", "centerline," + spine_seg,
                       "-o", reg_mask
                       ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
            # print(result.stdout)
            # print(result.stderr)

            # Register MT_OFF image
            #print("Registering MT OFF")
            command = [
                "sct_register_multimodal",
                "-i", MT_off_file,
                "-d", MT_file,
                "-dseg", spine_seg,
                "-param", "step=1,type=im,algo=slicereg,metric=CC",
                "-m", reg_mask,
                "-x", "spline",
                "-ofolder", output_folder
            ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
            # print(result.stdout)
            # print(result.stderr)

            #print("Computing MTR")
            MT_off_reg = os.path.join(output_folder, subj_id + '_' + scan_id + '_SPINE_MT_OFF_reg.nii.gz')
            MTR_file = os.path.join(output_folder, subj_id + '_' + scan_id + '_SPINE_MTR.nii.gz')
            command = [
                "sct_compute_mtr",
                "-mt0", MT_off_reg,
                "-mt1", MT_file,
                "-o", MTR_file,
            ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
            # print(result.stdout)
            # print(result.stderr)

            #print("Locating c3c4")
            c3c4_file = os.path.join(output_folder, subj_id + '_' + scan_id + '_SPINE_MT_c3c4.nii.gz')
            command = [
                "sct_label_utils",
                "-i", spine_seg,
                "-create-seg", "-1,4",
                "-o", c3c4_file
            ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
            # print(result.stdout)
            # print(result.stderr)

            #print("Registering template")
            command = [
                "sct_register_to_template",
                "-i", MT_file,
                "-s", spine_seg,
                "-ldisc", c3c4_file,
                "-ref", "subject",
                "-param", "step=1,type=seg,algo=centermassrot:step=2,type=seg,algo=bsplinesyn,slicewise=1",
                "-ofolder", output_folder
            ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
            # print(result.stdout)
            # print(result.stderr)

            #print("Warping template")
            warp_file = os.path.join(output_folder, 'warp_template2anat.nii.gz')
            command = [
                "sct_warp_template",
                "-d", MT_file,
                "-w", warp_file,
                "-ofolder", output_folder,
            ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
            # print(result.stdout)
            # print(result.stderr)

            #print("Extracting metrics")
            atlas_dir = os.path.join(output_folder, 'atlas')
            output_csv = os.path.join(output_folder, subj_id + '_' + scan_id + '_MTR_perslice.csv')
            img_shape = nib.load(spine_seg).get_fdata().shape
            command = [
                "sct_extract_metric",
                "-i", MTR_file,
                "-f", atlas_dir,
                "-l", "50",
                "-z", "0:" + str(img_shape[2] - 1),
                "-perslice", "1",
                "-o", output_csv,
            ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
            # print(result.stdout)
            # print(result.stderr)

            output_csv = os.path.join(output_folder, subj_id + '_' + scan_id + '_MTR_avg.csv')
            command = [
                "sct_extract_metric",
                "-i", MTR_file,
                "-f", atlas_dir,
                "-l", "50",
                "-z", "0:" + str(img_shape[2] - 1),
                "-o", output_csv,
            ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
            # print(result.stdout)
            # print(result.stderr)
            print("Done " + split_path[1])

if __name__ == '__main__':
    
    os.environ["PATH"] += os.pathsep + os.path.join('/home/j/jiwonoh/jglaist1/.virtualenvs/smhms/bin/')

    path = "/home/j/jiwonoh/jglaist1/scratch/data/SpinalCord/*_MT.nii.gz"
    MT_files = sorted(glob.glob(path))

    
    num_workers = 40
    pool = Pool(processes=num_workers)
    pool.map(process_mtr_spine, MT_files[44:])
    pool.close()
        