# extraction of sunlit pixels using spectral mean of pixel threshold, removing small regions and computing spectral indices

import arcpy
from arcpy.sa import *
import os

def spectralMeanMask(INPUT_RASTER, SPECTRAL_MEAN_THRESHOLD, FILL):
    print("spectral mean mask started!")

    arcpy.env.workspace = os.path.dirname(INPUT_RASTER)
    arcpy.env.overwriteOutput = 1

    # Extract bands
    blue = Float(Raster(INPUT_RASTER + r"\Band_1"))
    green = Float(Raster(INPUT_RASTER + r"\Band_2"))
    red = Float(Raster(INPUT_RASTER + r"\Band_3"))
    re = Float(Raster(INPUT_RASTER + r"\Band_4"))
    nir = Float(Raster(INPUT_RASTER + r"\Band_5"))

    # Compute spectral mean
    spectral_mean = (blue + green + red + re + nir)/5

    # Compute Statistics
    arcpy.management.BuildPyramidsandStatistics(spectral_mean, build_pyramids="NONE")

    # Extract by Attributes
    attExtract = ExtractByAttributes(spectral_mean, f"VALUE > {SPECTRAL_MEAN_THRESHOLD}")
    attExtract.save("tmp_extract.tif")

    # Extract by Mask
    outExtractByMask = ExtractByMask(INPUT_RASTER, "tmp_extract.tif", "INSIDE")
    outExtractByMask.save("tmp_extract2.tif")

    # prepare string for file name
    filename = os.path.splitext(os.path.basename(INPUT_RASTER))[0]
    filename = f'{filename}_spectral-mean_above{SPECTRAL_MEAN_THRESHOLD}_fill{FILL}.tif'

    # Fill
    filled = arcpy.sa.Con(arcpy.sa.IsNull("tmp_extract2.tif"), arcpy.sa.FocalStatistics("tmp_extract2.tif", arcpy.sa.NbrRectangle(FILL, FILL, 'CELL'), 'MEAN'), "tmp_extract2.tif")
    filled.save(filename)

    arcpy.management.Delete("tmp_extract.tif")
    arcpy.management.Delete("tmp_extract2.tif")

    print("spectral mean mask done!")
    print(f"raster saved: {os.path.dirname(INPUT_RASTER)}\\{filename}")

    return filename

def removeSmallRegions(filename, SMALL_REGIONS_THRESHOLD):
    print("removing small regions started!")

    # load input raster
    input_raster_obj = arcpy.Raster(filename)

    # Reclassify
    remap = [[input_raster_obj.minimum, input_raster_obj.maximum, 1]]

    reclassified = Reclassify(filename, "Value", RemapRange(remap))
    reclassified.save("reclassify.tif")

    # Region Group, Zonal geometry (compute area of regions), Set Null (too small areas set to NoData)
    mask_raster = SetNull(ZonalGeometry(RegionGroup("reclassify.tif", "EIGHT"), "VALUE",  "AREA") < SMALL_REGIONS_THRESHOLD, 1)
    mask_raster.save("mask_raster.tif")

    # Extract By Mask
    outExtractByMask = ExtractByMask(filename, "mask_raster.tif", "INSIDE")

    # prepare string for file name
    filename = os.path.splitext(os.path.basename(filename))[0]
    filename = f'{filename}_removed_small_reg_{SMALL_REGIONS_THRESHOLD}m2.tif'

    outExtractByMask.save(filename)

    arcpy.management.Delete("reclassify.tif")
    arcpy.management.Delete("mask_raster.tif")

    print("removing small regions done!")
    print(f"raster saved: {os.path.dirname(INPUT_RASTER)}\\{filename}")

    return filename

def computeIndices(filename):
    print("computing indices started!")

    # Extract bands
    blue = Float(Raster(filename + r"\Band_1"))
    green = Float(Raster(filename + r"\Band_2"))
    red = Float(Raster(filename + r"\Band_3"))
    re = Float(Raster(filename + r"\Band_4"))
    nir = Float(Raster(filename + r"\Band_5"))

    # Compute indices
    g_r = green/red
    g_b = green/blue
    r_b = red/blue
    nir_r = nir/red
    nir_g = nir/green
    nir_re = nir/re

    # List of all wanted bands in the output raster
    bands = [blue, green, red, re, nir, g_r, g_b, r_b, nir_r, nir_g, nir_re]

    # prepare string for file name
    filename = os.path.splitext(os.path.basename(filename))[0]
    filename = f'{filename}_indices.tif'

    # Composite Bands
    arcpy.management.CompositeBands(bands, filename)

    print(f"raster saved: {os.path.dirname(INPUT_RASTER)}\\{filename}")

def rasterEdit(INPUT_RASTER, SPECTRAL_MEAN_THRESHOLD, FILL, SMALL_REGIONS_THRESHOLD):
    filename = spectralMeanMask(INPUT_RASTER, SPECTRAL_MEAN_THRESHOLD, FILL)
    filename = removeSmallRegions(filename, SMALL_REGIONS_THRESHOLD)
    computeIndices(filename)


### INPUTS ###

# raster to edit
INPUT_RASTER = r'E:\raster.tif'

# spectral mean of a pixel threshold
SPECTRAL_MEAN_THRESHOLD = 1300

# fill parameter (px)
FILL = 3

# small regions threshold (m2)
SMALL_REGIONS_THRESHOLD = 1

##############

rasterEdit(INPUT_RASTER, SPECTRAL_MEAN_THRESHOLD, FILL, SMALL_REGIONS_THRESHOLD)