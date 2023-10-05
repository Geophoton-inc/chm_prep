# **chm_prep**

## What chm_prep does

High resolution airborne lidar Canopy Height Models (CHMs), or Digital Surface Models (DSM) often present **small cavities** over forest canopies (see the left part of the figure below). These are caused by laser pulses travelling deep below the generalized *crown envelope*. They may also show **spikes** caused by high noise if it was not properly removed from the point cloud before creating rasters products such as CHMs. Finally, no-data areas or **isolated no-data pixels**
 may also cause problems. chm_prep does several things to improve CHMs or DSMs before they are used for, say, individual tree crown (ITC) extraction, or image orthorectification using a lidar DSM as the 3D source. It was designed to:
- removes cavities and spikes;
- saturate the values to a minimum (e.g., 0.0 m for a CHM) and to a maximum;
- get rid of isolated no-data pixels.

It **leaves all non-problematic pixels unchanged**, so it is quite more targeted than, say, a simple median filter apply to an entire CHM. It is made for production, so it runs very fast, and is by default a batch mode processor. The user control all the processing parameters though an `.ini` file.

![Before and after applying chm_prep](chm_prep_example.png)

## Installing chm_prep

### Code structure

chm_prep is made of a Python script (`chm_prep.py`) which is responsible for I/O, the no-data management, and for launching the core cavity filling and spike removing algorithm, which, for efficiency reasons, is coded in C (`chm_prep.c`) and compiled to a shared library (`chm_prep.so`) called by the Python script.

### Installation

To install, place the .py and .so files in the same directory. Make sure to put the .so file corresponding to your OS (GNU/Linux or Windows).

### Compiling from source

If you prefer to compile for source (chm_prep.c), make sure to compile to a shared library. We hereby provide a single example of a compile command (for gcc):

    gcc -shared -o chm_prep.so -fPIC chm_prep.c

## Principles of the filtering algorithm

The algorithm steps are:
- run a Laplacian filter having a kernel size of *x* pixels;
- apply a threshold to the results to detect cavities
- apply a threshold to the resutls to detect spikes
- optionally, grow the detected anomalous pixels regions by dilation to remove the pixels in the immediate surroundings of the anomalous ones (dilation is usually 0 or 1 pixel, using a larger number will modify too many "good" pixels).
- fill in the holes left by the removal of the anomalous pixels by interpolating the values found on each hole's periphery;
- apply a median filter in the filled areas to smooth the interpolated values.

The algorithm can be applied in a single pass, or two passes. For high resolution models (e.g. a 25 cm, or 10 cm CHM), two passes are recommended. The first pass uses a bigger Laplacian kernel to get rid of larger cavities (or spikes), while the second pass targets the small pits and spikes. The use control the number of passes and the parameter values of each.

All non-anomalous pixel values are maintained.

## Using chm_prep

To run, adjust the parameter values in the `chm_prep.ini` file, save it, and run the Python script:

    python3 chm_prep.py

### The `chm_prep.ini` file

The chm_prep.ini file contains all the user parameters controlling the I/O as well as the algorithm itself. A template with "factory settings" is provided. It contains the parameters and their values, as well as inline comments to help the user properly fill in all the values. Make sure to follow the formatting standards in this template (e.g., no quotation marks around paths, etc.).

#### Input/Output parameters

All .tif files in the source_dir will be processed. The results will be written to the dest_dir, and the `_pr` (for _prep) will be added to the original file names.

#### Filtering parameters

The filtering parameters are written on a single, comma-delimited line, one line per pass (see the *Principle of the filtering algorithm section*). The order of the filtering parameters on a line is as follow:
- size of the Laplacian filter kernel (integer value, in pixels);
- threshold Laplacian value for detecting a cavity (all values above this value will be considered a cavity) - a positive float valueè
- threshold Laplacian value for detecting a spike (all values below this value will be considered a spike) - a negating float value;
- size of the median filter kernel (integer value, in pixels).
- dilation radius (integer value, in pixels)


Typical values for two passes over a for a 25 cm CHM could be:

`pass1_params=5,0.1,-0.1,3,0`

`pass2_params=3,0.1,-0.1,3,0`

Typical values for a single pass over a 50 cm CM could be:

`pass1_params=5,0.1,-0.1,3,0`

The number of passes (one or two) is controlled by the presence or absence of the pass2_params line.


#### Saturation parameters

The user can decide to saturate the values to a minimum, for example to avoid CHM values to be below 0 m. The user can also choose to set a maximum for a CHM. This may help to remove high noise that was not filtered out from the point cloud or limit the anomalous values caused by tree crowns hanging over a steep slope.
First, the floowing parameters must be set to True or False:
- `force_min_val`
- `force_max_val`

Then set the values of the min and max if the above paramters were set to True.


#### no-data parameters

No-data pixels can be present in a CHM or DSM for a variety of reasons: part of a tile was not scan, most pulses reaching a water body did not trigger a return, of the interpolation algorithm used to rasterize the lidar returns left a few isolated no-data values. These can create problems in the downstream processing steps (e.g., for ITC, etc.). Some no-data values represent mathematically impossible numbers, such as minus infinity or NaN (Not a Number), which sometimes lead to undesired behavior. cmp_prep lets the user keep, filter or modify any no-data pixels using three different schemes:
- transfer
- set_to_zero
- remove_small_holes

The first option, transfer, simple leaves the no-data pixels intact (but the user can change their values using the output_nodata_val parameter). The set_to_zero option will change the no-data pixels to zero. This can be practical for setting no-data values over a water body in a CHM to 0.0 m instead of having no-data in these areas, but we don't recommend this option for other use cases. Finally, the remove_small_holes option will leave the large no-data areas intact but will get rid of single pixel or small regions of no-data, such as those generated by certain rasterizing algorithms. The user must then provide a value for the hole_size_thr (hole size threshold) parameter. Holes having a pixel area smaller than hole_size_thr will be filled. The value of hole_size_thr must be an integer representing the number of pixels (pixel area) in a given no-data hole by interpolated values.


## Tile size, memory management, and buffering

chm_prep is designed for the standard case where a large lidar project is divided in rather small tiles. Running chm_prep on a very large file could cause the program to exit because of lack or memory. Moreover, edge effects can occur where cavities are very close to the edge of a raster lidar tile. Cavities or spikes might be left undetected in these slim areas. For this reason, it is recommended to buffer the tiles by at least the amount of pixels of the largest Lapalian kernel width before running chm_prep. The filtered output rasters can be cut back to their cores and eventually merged.

## Demo data




## References

To cite:
Fill in...

Scientific papers:
The core algorithm was first published in:
St-Onge, B., 2008. Methods for improving the quality of a true orthomosaic of Vexcel UltraCam images created using alidar digital surface model, Proceedings of the Silvilaser 2008, Edinburg, 555-562.# https://citeseerx.ist.psu.edu/document?repid=rep1&type=pdf&doi=81365288221f3ac34b51a82e2cfed8d58defb10e

A related version of the algorithm was later published in:
Ben-Arie, J. R., G. J. Hay, R. P. Powers, G. Castilla et B. St-Onge, 2009. Development and Evaluation of a Pit Filling
Algorithm for LiDAR Canopy Height Models, IEEE Transactions on Computers and Geosciences, 35:1940-1949
https://www.sciencedirect.com/science/article/abs/pii/S0098300409000624

## Licence

## Appendix - Factory settings of chm_prep.ini

Factory settings for a 25 cm CHM

Factory settings for a 50 cm CHM



