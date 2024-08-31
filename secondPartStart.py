# Usage: propy.bat secondPartStart.py rivers.shp

import arcpy, sys

# check if enough input arguments were provided, if not, terminate script
if len(sys.argv) < 2:
    print("ERROR: Not enough input arguments.\nUsage: secondPartStart.py lineFc")
    exit(-1)

# load feature class
fc = sys.argv[1]

# check if provided feature class is Polyline, if not, terminate script
desc = arcpy.Describe(fc)
if desc.shapeType != 'Polyline':
    print("ERROR: Input file is not Polyline.")
    exit(-1)

cursor = arcpy.da.SearchCursor(fc, ["SHAPE@"])

# count how many multiparts the feature class has
multi_parts = 0

# loop through features in feature class
for row in cursor:

    geom = row[0]

    # if the feature is singlepart, continue to next feature
    if geom.partCount < 2:
        continue

    else:
        # get the second part of the feature
        part = geom.getPart(1)

        # loop through points forming the second part
        first_point = True
        for point in part:

            # getting the coordinates of the first point
            if first_point:
                print(str(round(point.X)) + " " + str(round(point.Y)))
                first_point = False

            # no need to continue looping through other points - stopping the loop
            else:
                break

        # increment multipart
        multi_parts += 1

# if no multipart feature was found in the input feature class, print warning
if multi_parts == 0:
    print("WARNING: Input Polyline has no multipart feature.")

del cursor
