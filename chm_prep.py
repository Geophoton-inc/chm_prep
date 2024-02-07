# Program for removing cavities and spikes from a lidar Canopy Height Model (CHM).
# This part of the code only reads the input directorry and lists the files to be processed. It then sends OS calls to
# the chm_prep_process.py script to process the CHMs. This avoids loading the shared library cumulatively in memory
# to avoid memory leaks, as the shared library is not unloaded from memory after each call.

# Author: Benoît St-Onge, Geophoton inc. (www.geophoton.ca)
# Author's email: bstonge@protonmail.com
# See https://github.com/Geophoton-inc/cavity_fill_v_3/ for more information.
# License: GNU General Public license.
# Version: February 7, 2024

# The core algorithm was first published in:
# St-Onge, B., 2008. Methods for improving the quality of a true orthomosaic of Vexcel UltraCam images created using a
# lidar digital surface model, Proceedings of the Silvilaser 2008, Edinburg, 555-562.
# https://citeseerx.ist.psu.edu/document?repid=rep1&type=pdf&doi=81365288221f3ac34b51a82e2cfed8d58defb10e
# A related version of the algorithm was later published in:
# Ben-Arie, J. R., G. J. Hay, R. P. Powers, G. Castilla et B. St-Onge, 2009. Development and Evaluation of a Pit Filling
# Algorithm for LiDAR Canopy Height Models, IEEE Transactions on Computers and Geosciences, 35:1940-1949
# https://www.sciencedirect.com/science/article/abs/pii/S0098300409000624

# Note: this program calls an external C function (cavity_fill) compiled as a shared library (cavity_fill_3.so)
# and passes the CHM array and the parameters to it. It then writes the output array from the C function to a new
# raster file. The C shared library must reside in the same directory as this Python program. The proper version
# (Linux/GNU or Windows) must be installed.

import sys
import glob
import os
import configparser


def get_processing_parameters(cfile):
    # Get the processing parameters from the configuration file.

    # Read the configuration file.
    processing_parameters = configparser.RawConfigParser()
    try:
        processing_parameters.read_file(open(cfile))
    except OSError:
        print(cfile, 'configuration file not found. This file should be in the same folder as the application')
        print('Program halted')
        sys.exit(1)

    # Get the parameter values.
    proc_par = processing_parameters['PROCESSING_PARAMETERS']

    return proc_par


def main():

    # Read processing parameter from the chm_prep.ini file.
    proc_par = get_processing_parameters('chm_prep.ini')
    # Get the processing parameter values.
    source_dir = proc_par['source_dir']

    # Create a list of input .tif files.
    input_chms = glob.glob(os.path.join(source_dir, '*.tif'))
    if len(input_chms) == 0:
        print('No .tif files found in', source_dir)
        print('Program halted')
        sys.exit(1)

    # Loop through the input CHMs.
    for index, chm_file in enumerate(input_chms):
        print(f'Processing CHM {index + 1} of {len(input_chms)}: {chm_file}')

        os.system(f'python chm_prep_process.py {chm_file}')


if __name__ == '__main__':
    main()
