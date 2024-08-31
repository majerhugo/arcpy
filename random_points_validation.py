import arcpy
from arcpy import env
from arcpy.sa import *
import random
import os

def calculatePointAmount(INPUT_SHP, INPUT_RASTER, POINT_AMOUNT):

    arcpy.management.BuildPyramidsandStatistics(INPUT_RASTER, build_pyramids="NONE")

    # load raw not yet classified raster
    input_raster_obj = arcpy.Raster(INPUT_RASTER)

    # Reclassify raster to 0 (for NoData) or 1
    remap = [[input_raster_obj.minimum, input_raster_obj.maximum, 1]]

    reclassified = Reclassify(INPUT_RASTER, "Value", RemapRange(remap))
    reclassified.save("reclassify_class1.tif")

    reclassified = arcpy.sa.Con(arcpy.sa.IsNull("reclassify_class1.tif"), 0, "reclassify_class1.tif", "Value = 1")
    reclassified.save("reclassified_raster.tif")

    # Tabulate Area (output is nonspatial table containing area of classes 0, 1 in ground truth polygons)
    TabulateArea(INPUT_SHP, "FID", 'reclassified_raster.tif', "Value", "tabulka.dbf")

    arcpy.MakeFeatureLayer_management(INPUT_SHP, "tren_dat_layer")
    arcpy.management.MakeTableView("tabulka.dbf", "tabulka_layer")

    # Join the nonspatial table to ground truth polygons layer
    arcpy.AddJoin_management("tren_dat_layer", 'FID', "tabulka_layer", "FID_")

    # Save join
    arcpy.CopyFeatures_management("tren_dat_layer", "trenovacie_data_joined.shp")

    # Dissolve by classname, create field with count of ground truth polygons and total area of class 1 pixels
    arcpy.management.Dissolve("trenovacie_data_joined.shp", "dissolved.shp", ['Classname'], [['FID','COUNT'],['VALUE_1','SUM']], "MULTI_PART")

    # Find the total area field in the attribute table
    fields = arcpy.ListFields('dissolved.shp')
    sum_field = [f.name for f in fields if 'SUM' in f.name]

    # Get total area of all ground truth polygons
    summed_area = 0
    with arcpy.da.SearchCursor('dissolved.shp', sum_field) as cursor:
        for row in cursor:
            summed_area += row[0]

    print(f"Total area of ground truth polygons (only area with existent raster data, NoData pixels omitted): {summed_area} m2")

    # Get the amount of validation point for 1 m2
    point_per_m2 = POINT_AMOUNT / summed_area

    # Calculate the amount of validation points for each class
    druhy = []
    points_amount = []
    with arcpy.da.SearchCursor('dissolved.shp', ['Classname', sum_field]) as cursor:
        for row in cursor:
            druhy.append(row[0])
            points = int(round(row[1] * point_per_m2, 0))
            points_amount.append(points)

    # Check if the amount of validation points equals to desired point amount
    while sum(points_amount) != POINT_AMOUNT:

        # If the amount is higher, delete a validation point of a random class
        if sum(points_amount) > POINT_AMOUNT:
            random_int = random.randint(0, len(druhy) - 1)
            points_amount[random_int] -= 1

        # If the amount is lower, add a validation point to a random class
        elif sum(points_amount) < POINT_AMOUNT:
            random_int = random.randint(0, len(druhy) - 1)
            points_amount[random_int] += 1

    print(f"{sum(points_amount)} points were stratified to {len(druhy)} classes!")

    # Add a field for the calculated amount of validation points
    arcpy.AddField_management("dissolved.shp", "amount", "SHORT")

    # Insert the amount of validation points to created field
    pointer = 0
    with arcpy.da.UpdateCursor("dissolved.shp", "amount") as cursor:
         for row in cursor:
             row[0] = points_amount[pointer]
             cursor.updateRow(row)
             pointer += 1

    arcpy.management.Delete("reclassify_class1.tif")
    arcpy.management.Delete("reclassified_raster.tif")
    arcpy.management.Delete("tabulka.dbf")
    arcpy.management.Delete("trenovacie_data_joined.shp")

def getRandomPoints(INPUT_CLASSIFICATION, V_DATASET, MIN_DISTANCE, RANDOM_POINTS_NAME):

    # load the classification that will be validated
    input_class_obj = arcpy.Raster(INPUT_CLASSIFICATION)

    # reclassify all classes to 1, omit Masked class
    remap = [[input_class_obj.minimum, input_class_obj.maximum - 1, 1]]

    # if in the classification isn't Masked class, use this
    #remap = [[input_class_obj.minimum, input_class_obj.maximum, 1]]

    reclassified = Reclassify(input_class_obj, "Value", RemapRange(remap))
    reclassified.save("reclassify.tif")

    # Extract just class 1 from reclassified raster
    attExtract = ExtractByAttributes("reclassify.tif", "VALUE = 1")
    attExtract.save("attExtract.tif")

    # Convert it to polygon
    arcpy.conversion.RasterToPolygon("attExtract.tif", "raster2polygon.shp", "NO_SIMPLIFY")

    arcpy.management.Delete("reclassify.tif")
    arcpy.management.Delete("attExtract.tif")

    # Compute intersect of reclassified polygon classification with validation polygons dataset - later generated validation
    # points needed only in this intersection
    arcpy.analysis.Intersect(['raster2polygon.shp', V_DATASET], 'intersect.shp')
    arcpy.management.Delete("raster2polygon.shp")

    # Remove the edges of intersections - generation of validation points on the very edges of validation polygons not desirable
    arcpy.analysis.Buffer('intersect.shp', 'buffer.shp', "-0,05 Meters")

    # Dissolve the intersections by classes
    arcpy.management.Dissolve('buffer.shp', 'dissolve.shp', "CLASSNAME", "")

    arcpy.management.Delete("intersect.shp")
    arcpy.management.Delete("buffer.shp")

    # join it with the layer in which the amounts of validation points for each class is stored
    arcpy.MakeFeatureLayer_management('dissolve.shp', "layer1")
    arcpy.MakeFeatureLayer_management("dissolved.shp", "layer2")
    arcpy.AddJoin_management("layer1", 'Classname', "layer2", 'Classname')
    arcpy.CopyFeatures_management("layer1", "point_amounts.shp")

    arcpy.management.Delete("dissolve.shp")
    arcpy.management.Delete("dissolved.shp")

    # Generate random points according to the calculated amounts of validation points
    arcpy.management.CreateRandomPoints(arcpy.env.workspace, 'get_random_points.shp', "point_amounts.shp", "", "amount",
                                        MIN_DISTANCE)

    # Spatial Join for assigning the ground truth class to generated random points
    fieldmappings1 = arcpy.FieldMappings()
    fieldmappings1.addTable('get_random_points.shp')

    fieldmappings2 = arcpy.FieldMappings()
    fieldmappings2.addTable('point_amounts.shp')

    classname_field = fieldmappings2.findFieldMapIndex("Classname")
    fieldmap = fieldmappings2.getFieldMap(classname_field)
    fieldmap.mergeRule = "first"

    fieldmappings1.addFieldMap(fieldmap)

    arcpy.analysis.SpatialJoin('get_random_points.shp', "point_amounts.shp", f'{RANDOM_POINTS_NAME}', "#", "#",
                               fieldmappings1)

    arcpy.management.Delete("get_random_points.shp")
    arcpy.management.Delete("point_amounts.shp")

    print(f"Random points saved to {os.path.dirname(INPUT_CLASSIFICATION)}\\{RANDOM_POINTS_NAME}")


#### INPUTS ####

# all ground truth polygons (for calculating the amounts of validation point for each class)
INPUT_SHP = r'E:\ground_truth_polygons.shp'

# raw raster which was later classified
INPUT_RASTER = r'E:\raster.tif'

# polygon validation dataset (polygons inside which the validation points will be generated)
V_DATASET = r'E:\validation_polygons.shp'

# classification to be validated
INPUT_CLASSIFICATION = r'E:\classification.tif'

# desired validation point amount
POINT_AMOUNT = 3393

# desired minimal distance between validation points
MIN_DISTANCE = 0.3

# name for the validation points layer
RANDOM_POINTS_NAME = 'random_points.shp'

################


#### SCRIPT ####
arcpy.env.workspace = os.path.dirname(INPUT_CLASSIFICATION)
arcpy.env.overwriteOutput = 1
arcpy.env.qualifiedFieldNames = 0
calculatePointAmount(INPUT_SHP, INPUT_RASTER, POINT_AMOUNT)
getRandomPoints(INPUT_CLASSIFICATION, V_DATASET, MIN_DISTANCE, RANDOM_POINTS_NAME)