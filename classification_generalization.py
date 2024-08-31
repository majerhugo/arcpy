# generalizing of a classification

import arcpy
from arcpy.sa import *
import os

### INPUTS ###
INPUT_CLASSIFICATION = r'E:\classification.dat'
THRESHOLD = 100
########

## SCRIPT ##
arcpy.env.workspace = os.path.dirname(INPUT_CLASSIFICATION)
arcpy.env.overwriteOutput = 1

filename = os.path.splitext(os.path.basename(INPUT_CLASSIFICATION))[0]
filename = f'{filename}_nibble_{THRESHOLD}'

# Region Group
rg_out = RegionGroup(INPUT_CLASSIFICATION, "EIGHT")
rg_out.save("tmp_rg_out.tif")

# Set Null
sn_out = SetNull("tmp_rg_out.tif", 1, f"COUNT < {THRESHOLD}")
sn_out.save("tmp_sn_out.tif")

# Nibble
nb_out = Nibble(INPUT_CLASSIFICATION, "tmp_sn_out.tif")
nb_out.save(f'{filename}.tif')

# Export as ENVI
#arcpy.management.CopyRaster(f'{filename}.tif', f'{filename}.dat', pixel_type="4_BIT", format="ENVI")

arcpy.management.Delete("tmp_rg_out.tif")
arcpy.management.Delete("tmp_sn_out.tif")
