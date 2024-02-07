# Program for removing cavities and spikes from a lidar Canopy Height Model (CHM). This part of the code processes one
# CHM at a time. It is called by the chm_prep.py script to process the CHMs. It can be used as a standalone script.
# The full parth and name of the CHM to process is passed as a command line argument. For example:
# python chm_prep_process.py /path/to/chm.tif

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

from ctypes import c_void_p, c_int, c_float, cdll
from numpy.ctypeslib import ndpointer
import numpy as np
from osgeo import gdal
from osgeo.gdal_array import CopyDatasetInfo, BandWriteArray, BandReadAsArray
import sys
import glob
import os
import configparser


class Params:
    # This class contains the processing parameters for a single pass of the cavity filling algorithm.
    def __init__(self, pass_params):
        try:
            self.lap_size = int(pass_params[0])  # Size of the Laplacian filter in pixels.
        except ValueError:
            print('Invalid parameter value for Laplacian filter in pixels in chm_prep.ini file. '
                  'This value must be an integer.')
            print('Program halted')
            sys.exit(1)
        try:
            self.thr_lap = float(pass_params[1])   # Threshold value for the Laplacian filter.
        except ValueError:
            print('Invalid parameter value for the Laplacian filter cavity threshold in chm_prep.ini file. '
                  'This value must be a float or an integer.')
            print('Program halted')
            sys.exit(1)
        try:
            self.thr_spk = float(pass_params[2])   # Threshold value for the Laplacian filter.
        except ValueError:
            print('Invalid parameter value for the Laplacian filter spike threshold in chm_prep.ini file. '
                  'This value must be a float or an integer.')
            print('Program halted')
            sys.exit(1)
        try:
            self.med_size = int(pass_params[3])   # Size of the median filter in pixels.
        except ValueError:
            print('Invalid parameter value for the median filter in pixels in chm_prep.ini file. '
                  'This value must be an integer.')
            print('Program halted')
            sys.exit(1)
        try:
            self.dil_radius = int(pass_params[4])   # Radius of the dilation filter in pixels.
        except ValueError:
            print('Invalid parameter value for the dilation filter in pixels in chm_prep.ini file. '
                  'This value must be an integer.')
            print('Program halted')
            sys.exit(1)


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

    chm_file = sys.argv[1]
    # Read processing parameter from the chm_prep.ini file.
    proc_par = get_processing_parameters('chm_prep.ini')
    # Get the processing parameter values.
    dest_dir = proc_par['dest_dir']
    pass1_params = proc_par['pass1_params'].split(',')
    try:  # If the user asked for a second pass.
        pass2_params = proc_par['pass2_params'].split(',')
    except KeyError:  # If the user did not ask for a second pass.
        pass2_params = None
    force_min_val = proc_par.getboolean('force_min_val')
    if force_min_val:
        min_val = proc_par.getfloat('min_val')
    force_max_val = proc_par.getboolean('force_max_val')
    if force_max_val:
        max_val = proc_par.getfloat('max_val')
    nodata_processing = proc_par['nodata_processing']
    if nodata_processing == 'remove_small_holes':
        hole_size_thr = int(proc_par['hole_size_thr'])
    output_nodata_val = float(proc_par['output_nodata_val'])

    # Create a list of 1 or 2 objects of class Params (depending on the user asking for 1 or 2 passes).
    params_list = [Params(pass1_params)]
    if pass2_params is not None:  # If the user asked for 2 passes.
        params_list.append(Params(pass2_params))

    # If the destination folder does not exist, create it.
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    # Get the operating system ID to load the proper shared library.
    os_id = sys.platform
    if os_id != 'linux' and os_id != 'win32':
        print('The shared library (chm_prep_linux.so or chm_prep_win.so) for your operating system was not found.')
        print('Program halted')
        sys.exit(1)
    # Load the C shared library containing the cavity_fill() function.
    lib = cdll.LoadLibrary('./chm_prep_' + os_id + '.so')
    chm_prep = lib.chm_prep # Get the function from the library.

    # Loop through the input CHMs.

    # Open the input CHM.
    chm = gdal.Open(chm_file, gdal.GA_ReadOnly)
    if chm is None:
        print(f'Could not open {chm_file}')
        sys.exit(1)
    chm_ncol = chm.RasterXSize
    chm_nlin = chm.RasterYSize
    chm_band = chm.GetRasterBand(1)
    chm_array = BandReadAsArray(chm_band)

    # Create the nodata mask.
    input_nodata_val = chm_band.GetNoDataValue()

    if input_nodata_val is not None:  # If the no-data value is defined.
        # Check is input_nodata_val is not a number (NaN).
        # For the case where the no-data values is defined as not-a-number (NaN).
        # See: https://www.mail-archive.com/gdal-dev@lists.osgeo.org/msg36140.html
        if np.isnan(input_nodata_val):
            nodata_mask = np.isnan(chm_array)  # Create the no-data mask from NaN.
        else:
            nodata_mask = chm_array == input_nodata_val  # Create the no-data mask from number.

    if nodata_processing == 'set_to_zero':
        chm_array[nodata_mask] = 0
    else:
        if nodata_processing == 'remove_small_holes':
            from skimage import morphology
            chm_array[nodata_mask] = 0  # Set to zero so the nodata values can be filled.
            # Remove small holes (a double invert is necessary for the logic of the morphology function).
            nodata_mask = np.invert(morphology.remove_small_holes(np.invert(nodata_mask), hole_size_thr))

    # Create output file name.
    output_file_name = os.path.join(dest_dir, os.path.basename(chm_file).replace('.tif', '_prep.tif'))
    # Create output image.
    driver = gdal.GetDriverByName("Gtiff")
    out_chm = driver.Create(output_file_name, chm.RasterXSize, chm.RasterYSize, 1, gdal.GDT_Float32)
    if out_chm is None:
        print('Cannot create output file ', output_file_name)
        print('Program halted')
        sys.exit(1)
    CopyDatasetInfo(chm, out_chm)
    array_out = out_chm.GetRasterBand(1)

    # Create a zero array with a proper memory address for storing the CHM array.
    array_zero = np.zeros((chm_nlin, chm_ncol), dtype=float)

    # Loop through the passes (1 or 2).
    for pass_params in params_list:
        print('    Pass', params_list.index(pass_params) + 1, 'of', len(params_list))

        # Transfer the values of CHM array into array. This fixes the unusable address issue if chm_array is
        # transferred directly to the C function.
        array = array_zero + chm_array

        chm_prep.restype = ndpointer(dtype=c_float,  # Set result type.
                                 shape=(chm_nlin, chm_ncol))  # Set result shape.

        # Call cavity_fill() function in the C shared library and pass the input array pointer to the function.
        chm_array = chm_prep(c_void_p(array.ctypes.data),
                                c_int(chm_nlin),
                                c_int(chm_ncol),
                                c_int(pass_params.lap_size),
                                c_float(pass_params.thr_lap),
                                c_float(pass_params.thr_spk),
                                c_int(pass_params.med_size),
                                c_int(pass_params.dil_radius)
                                )

    # Force the minimum and maximum values if requested by the user.
    if force_min_val:
        chm_array[chm_array < min_val] = min_val
    if force_max_val:
        chm_array[chm_array > max_val] = max_val

    if input_nodata_val is not None:  # If the no-data value is defined.
        if nodata_processing == 'transfer' or nodata_processing == 'remove_small_holes':
            chm_array[nodata_mask] = output_nodata_val

    # Set output nodata value.
    array_out.SetNoDataValue(output_nodata_val)
    BandWriteArray(array_out, chm_array)
    # Nullify the pointers to the input and output files.
    chm = None
    out_chm = None


if __name__ == '__main__':
    main()
