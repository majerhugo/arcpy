# data folder: C:\SKOLA\PROGRAMOVANI_GIS\cviceni4\ukol
# propy.bat multiMerge.py C:\SKOLA\PROGRAMOVANI_GIS\cviceni4\ukol point_out line_out polygon_out

import arcpy, sys

arcpy.env.overwriteOutput = 1

arcpy.env.workspace = str(sys.argv[1])

point_out = sys.argv[2]
line_out = sys.argv[3]
polygon_out = sys.argv[4]

lines = arcpy.ListFeatureClasses(feature_type='Line')
polygons = arcpy.ListFeatureClasses(feature_type='Polygon')
points = arcpy.ListFeatureClasses(feature_type='Point')

# check if in the data folder are results from previous Merge, if there are, delete them
if str(point_out+".shp") in points:
    arcpy.Delete_management(point_out+".shp")
    points.remove(point_out+".shp")

if str(line_out+".shp") in lines:
    arcpy.Delete_management(line_out+".shp")
    lines.remove(line_out + ".shp")

if str(polygon_out+".shp") in polygons:
    arcpy.Delete_management(polygon_out+".shp")
    polygons.remove(polygon_out + ".shp")

print('Linie:', lines)
print('Polygony:', polygons)
print('Body:', points)

arcpy.Merge_management(lines, line_out)
arcpy.Merge_management(polygons, polygon_out)
arcpy.Merge_management(points, point_out)
