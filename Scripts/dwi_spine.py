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

def process_dwi_spine(DWI_file):
    split_path = os.path.split(DWI_file)

    #print(split_path[1])
    subj_id = split_path[1].split('_')[0]
    scan_id = split_path[1].split('_')[1]
    output_folder = os.path.join(split_path[0], 'DWI', subj_id + '_' + scan_id)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    bvec_file = DWI_file[0:-7] + '.bvec'
    bval_file = DWI_file[0:-7] + '.bval'

    print("Starting segmenting spine " + split_path[1])
    # Segment spine
    DWI_mean_file = os.path.join(output_folder, subj_id + '_' + scan_id + '_SPINE_DWI_mean.nii.gz')
    command = ['sct_maths',
               '-i', DWI_file,
               '-mean', 't',
               '-o', DWI_mean_file
               ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
    #print(result.stdout)
    #print(result.stderr)

    # Initial DWI spine seg
    command = ['sct_propseg',
               '-i', DWI_mean_file,
               '-c', 'dwi',
               '-ofolder', output_folder
               ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
    #print(result.stdout)
    #print(result.stderr)

    DWI_mask_file = os.path.join(output_folder, subj_id + '_' + scan_id + '_SPINE_DWI_mask.nii.gz')
    DWI_mean_centerline_file = os.path.join(output_folder, subj_id + '_' + scan_id + '_SPINE_DWI_mean_centerline.nii.gz')

    command = ['sct_create_mask',
               '-i', DWI_mean_file,
               '-p', 'centerline,' + DWI_mean_centerline_file,
               '-size','35mm',
               '-o', DWI_mask_file
               ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
    #print(result.stdout)
    #print(result.stderr)

    command = ['sct_dmri_moco',
               '-i', DWI_file,
               '-bvec',bvec_file,
               '-bval',bval_file,
               '-m',DWI_mask_file,
               '-ofolder', output_folder
               ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
    #print(result.stdout)
    #print(result.stderr)


    DWI_mean_moco_file = os.path.join(output_folder, subj_id + '_' + scan_id + '_SPINE_DWI_moco_dwi_mean.nii.gz')

    command = ["sct_deepseg_sc",
               "-i", DWI_mean_moco_file,
               "-c", "dwi",
               "-ofolder", output_folder
               ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
    #print(result.stdout)
    #print(result.stderr)

    DWI_moco_file = os.path.join(output_folder, subj_id + '_' + scan_id + '_SPINE_DWI_moco.nii.gz')
    DWI_output_prefix = os.path.join(output_folder, subj_id + '_' + scan_id + '_SPINE_DTI_')
    command = ["sct_dmri_compute_dti",
               "-i", DWI_moco_file,
               '-bval',bval_file,
               '-bvec',bvec_file,
               "-o", DWI_output_prefix
               ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
    #print(result.stdout)
    #print(result.stderr)

    spine_seg = os.path.join(output_folder, subj_id + '_' + scan_id + '_SPINE_DWI_moco_dwi_mean_seg.nii.gz')
    c3c4_file = os.path.join(output_folder, subj_id + '_' + scan_id + '_SPINE_DWI_c3c4.nii.gz')
    command = ["sct_label_utils",
               "-i", spine_seg,
               "-create-seg", "-1,4",
               "-o", c3c4_file
              ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)

    command = ["sct_register_to_template",
                "-i",DWI_mean_moco_file,
                "-s",spine_seg,
                "-ldisc",c3c4_file,
                "-ref","subject",
                "-param","step=1,type=seg,algo=centermassrot:step=2,type=seg,algo=bsplinesyn,slicewise=1",
                "-ofolder",output_folder
            ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,env=os.environ)


    warp_file = os.path.join(output_folder,'warp_template2anat.nii.gz')
    command = [
        "sct_warp_template",
        "-d",DWI_mean_moco_file,
        "-w",warp_file,
        "-ofolder",output_folder,
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,env=os.environ)
    #print(result.stdout)
    #print(result.stderr)


    #FA
    atlas_dir = os.path.join(output_folder,'atlas')
    output_csv = os.path.join(output_folder,subj_id+'_'+scan_id+'_FA_perslice.csv')
    metric_file = os.path.join(output_folder, subj_id + '_' + scan_id + '_SPINE_DTI_FA.nii.gz')
    img_shape = nib.load(spine_seg).get_fdata().shape
    command = [
        "sct_extract_metric",
        "-i",metric_file,
        "-f",atlas_dir,
        "-l","50",
        "-z","0:"+str(img_shape[2]-1),
        "-perslice","1",
        "-o",output_csv,
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,env=os.environ)

    output_csv = os.path.join(output_folder,subj_id+'_'+scan_id+'_FA_avg.csv')
    command = [
        "sct_extract_metric",
        "-i",metric_file,
        "-f",atlas_dir,
        "-l","50",
        "-z","0:"+str(img_shape[2]-1),
        "-o",output_csv,
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,env=os.environ)
    #print(result.stdout)
    #print(result.stderr)

    #MD
    output_csv = os.path.join(output_folder,subj_id+'_'+scan_id+'_MD_perslice.csv')
    metric_file = os.path.join(output_folder, subj_id + '_' + scan_id + '_SPINE_DTI_MD.nii.gz')
    command = [
        "sct_extract_metric",
        "-i",metric_file,
        "-f",atlas_dir,
        "-l","50",
        "-z","0:"+str(img_shape[2]-1),
        "-perslice","1",
        "-o",output_csv,
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,env=os.environ)

    output_csv = os.path.join(output_folder,subj_id+'_'+scan_id+'_MD_avg.csv')
    command = [
        "sct_extract_metric",
        "-i",metric_file,
        "-f",atlas_dir,
        "-l","50",
        "-z","0:"+str(img_shape[2]-1),
        "-o",output_csv,
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,env=os.environ)
    #print(result.stdout)
    #print(result.stderr)

    #RD
    output_csv = os.path.join(output_folder,subj_id+'_'+scan_id+'_RD_perslice.csv')
    metric_file = os.path.join(output_folder, subj_id + '_' + scan_id + '_SPINE_DTI_RD.nii.gz')
    command = [
        "sct_extract_metric",
        "-i",metric_file,
        "-f",atlas_dir,
        "-l","50",
        "-z","0:"+str(img_shape[2]-1),
        "-perslice","1",
        "-o",output_csv,
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,env=os.environ)

    output_csv = os.path.join(output_folder,subj_id+'_'+scan_id+'_RD_avg.csv')
    command = [
        "sct_extract_metric",
        "-i",metric_file,
        "-f",atlas_dir,
        "-l","50",
        "-z","0:"+str(img_shape[2]-1),
        "-o",output_csv,
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,env=os.environ)
    #print(result.stdout)
    #print(result.stderr)


    #AD
    output_csv = os.path.join(output_folder,subj_id+'_'+scan_id+'_AD_perslice.csv')
    metric_file = os.path.join(output_folder, subj_id + '_' + scan_id + '_SPINE_DTI_AD.nii.gz')
    command = [
        "sct_extract_metric",
        "-i",metric_file,
        "-f",atlas_dir,
        "-l","50",
        "-z","0:"+str(img_shape[2]-1),
        "-perslice","1",
        "-o",output_csv,
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,env=os.environ)

    output_csv = os.path.join(output_folder,subj_id+'_'+scan_id+'_AD_avg.csv')
    command = [
        "sct_extract_metric",
        "-i",metric_file,
        "-f",atlas_dir,
        "-l","50",
        "-z","0:"+str(img_shape[2]-1),
        "-o",output_csv,
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,env=os.environ)
    #print(result.stdout)
    #print(result.stderr)
    print("Done " + split_path[1])

if __name__ == '__main__':
    
    os.environ["PATH"] += os.pathsep + os.path.join('/home/j/jiwonoh/jglaist1/.virtualenvs/smhms/bin/')

    path = "/home/j/jiwonoh/jglaist1/scratch/data/SpinalCordDWI/*_SPINE_DWI.nii.gz"
    DWI_files = sorted(glob.glob(path))

    
    num_workers = 40
    pool = Pool(processes=num_workers)
    pool.map(process_dwi_spine, DWI_files)
    pool.close()
        
