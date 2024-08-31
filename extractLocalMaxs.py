# Usage: propy.bat extractLocalMaxs.py dmr.tif localmaxs.shp

import arcpy, sys, os

# check if enough input arguments were provided, if not, terminate script
if len(sys.argv) < 3:
    print("ERROR: Not enough input arguments.\nUsage: extractLocalMaxs.py in_raster out_fc")
    exit(-1)


def pixToPointGeom(r, s, raster):
    # converting the centroid of raster pixel to arcpy.Point

    origin_x = raster.extent.XMin + 0.5 * raster.meanCellWidth
    origin_y = raster.extent.YMax + 0.5 * raster.meanCellHeight

    x = origin_x + s * raster.meanCellWidth
    y = origin_y + - r * raster.meanCellHeight

    pnt = arcpy.Point(x, y)

    return pnt


arcpy.env.overwriteOutput = 1

# make arcpy.Raster from provided raster file
in_raster = arcpy.Raster(str(sys.argv[1]))

# get the absolute path of the provided raster file
raster_path = os.path.abspath(sys.argv[1])

# set the workspace to the folder in which the provided raster file is
arcpy.env.workspace = os.path.dirname(raster_path)

# get the name of the output feature class
out_fc = str(sys.argv[2])

# create point feature class with provided name, coord system same as provided raster file
arcpy.CreateFeatureclass_management(arcpy.env.workspace, out_fc, "POINT", "#", "#", "#", in_raster.spatialReference)

# add new field to the feature class, field will contain the height of points in decimal numbers
arcpy.AddField_management(out_fc, "VYSKA", "DOUBLE")


# get raster dimensions
width = in_raster.width
height = in_raster.height

# loop through raster pixels
for row, column in in_raster:

    # skip pixels at the raster edge
    if row < 1 or column < 1 or row > (height - 2) or column > (width - 2):
        continue

    # get the value of the processed pixel
    pixel_value = in_raster[row, column]

    # initializing the count of adjacent pixels having lower value
    smaller_values = 0

    # loop through pixels adjacent to processed pixel (3 x 3 window)
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):

            # if adjacent pixel has lower value than the processed pixel, increment the count
            if in_raster[row + i, column + j] < pixel_value:
                smaller_values += 1

    # if all 8 adjacent pixels had lower value, consider the processed pixel as local maximum
    if smaller_values == 8:

        # convert local maximum pixel to arcpy.Point
        pnt = pixToPointGeom(row, column, in_raster)

        # insert the point with its height to the output feature class
        cursor = arcpy.da.InsertCursor(out_fc, ["SHAPE@", "VYSKA"])
        cursor.insertRow((arcpy.PointGeometry(pnt), pixel_value))

del cursor
