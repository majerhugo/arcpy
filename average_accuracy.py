import arcpy
from arcpy.sa import *
import os

def readHDRfile(INPUT_CLASSIFICATION):
    hdr_file = f"{os.path.dirname(INPUT_CLASSIFICATION)}\\{os.path.splitext(os.path.basename(INPUT_CLASSIFICATION))[0]}.hdr"

    lines = []
    classes_line = 0
    with open(fr"{hdr_file}") as f:

        for count, line in enumerate(f, 1):
            if "class names" in line:
                classes_line = count + 1

            if count == classes_line:
                lines.append(line)

    # cely riadok ulozeny ako jeden element listu - rozdel ho na viacero elementov
    split = [e.split(', ') for e in lines]

    # vonkajsi list prec
    [split] = split

    # z posledneho elementu prec nepotrebne znaky a prepis posledny element
    split[-1] = (split[-1])[:-2]

    ##### odstran prvy element Unclassified, nepotrebujem ho;; mozno lepsie najst index triedy Unclass a zmazat ten, lepsie ako takto natvrdo...
    split.pop(0)

    # daj vsetko na male pismena
    split = [x.lower() for x in split]

    return split

def getPercentages(INPUT_CLASSIFICATION, VAL_DATA):
    arcpy.MakeFeatureLayer_management(VAL_DATA, "val_dat_layer")
    arcpy.management.BuildPyramidsandStatistics(INPUT_CLASSIFICATION, build_pyramids="NONE")

    # Tabulate Area - get the area of each classification class in each validation polygon
    TabulateArea("val_dat_layer", "FID", INPUT_CLASSIFICATION, "Value", "TabArea_table.dbf")
    arcpy.management.MakeTableView("TabArea_table.dbf", "TabArea_layer")

    # Get the fields in which the area of each classification class in validation polygon is stored
    fields = arcpy.ListFields("TabArea_layer")
    fields_list = [f.name for f in fields]

    values_list = [field for field in fields_list if "VALUE" in field]

    # Create a new field where total count of pixels will be stored
    arcpy.AddField_management("TabArea_layer", "px_total", "DOUBLE")

    # Read .hdr file to get the classification classes
    split = readHDRfile(INPUT_CLASSIFICATION)

    # convert area to pixel counts
    for value_field in values_list:
        arcpy.management.CalculateField("TabArea_layer", value_field, f"!{value_field}! * 100", "PYTHON3")

    # calculate the total amount of pixels
    arcpy.management.CalculateField("TabArea_layer", "px_total", "" "!" + '!+!'.join(values_list[:-1]) + "!" "", "PYTHON3")

    # create fields for storing the percentage of pixels
    for druh in split[:-1]:
        arcpy.AddField_management("TabArea_layer", f"{druh}_pc", "DOUBLE")

    # delete records with 0 pixels
    with arcpy.da.UpdateCursor("TabArea_layer", "px_total") as cursor:
        for row in cursor:
            if row[0] == 0:
                cursor.deleteRow()

    # calculate the proportions
    zipped = list(zip(split[:-1], values_list[:-1]))
    for i in zipped:
        arcpy.management.CalculateField("TabArea_layer", f"{i[0]}_pc", f"(!{i[1]}! / !px_total!) * 100", "PYTHON3")

    # join the resulting nonspatial table to validation polygons layer
    arcpy.AddJoin_management("val_dat_layer", 'FID', 'TabArea_layer', "FID_")

    # save join
    arcpy.CopyFeatures_management("val_dat_layer", "validated.shp")

    arcpy.Delete_management("val_dat_layer")
    arcpy.Delete_management("TabArea_layer")
    arcpy.Delete_management("TabArea_table.dbf")

    # get all fields with proportions
    percent_fields = [f"{druh}_pc" for druh in split]
    percent_fields.insert(0, 'classname')

    return split, percent_fields

def getAverageAccuracy(split, percent_fields):

    result_dict = {druh: 0 for druh in split[:-1]}

    for druh in split[:-1]:

        percents_sum = 0
        counter = 0

        # generating confusion matrix
        with arcpy.da.SearchCursor("validated.shp", percent_fields[:-1]) as cursor:

            # loop through every validation polygon
            for row in cursor:

                if row[0] == druh:

                    percents_sum += row[split.index(str(row[0])) + 1]
                    counter += 1

        accuracy = percents_sum/counter
        result_dict[druh] = round(accuracy, 2)

    print("PRIEMERNA USPESNOST DRUHU:")
    print(result_dict)

    arcpy.Delete_management("validated.shp")

#### INPUTS ####

VAL_DATA = r'E:\validation_polygons.shp'
INPUT_CLASSIFICATION = r'E:\classification.dat'

################

#### SCRIPT ####
arcpy.env.workspace = os.path.dirname(INPUT_CLASSIFICATION)
arcpy.env.overwriteOutput = 1
arcpy.env.qualifiedFieldNames = 0

split, percent_fields = getPercentages(INPUT_CLASSIFICATION, VAL_DATA)
getAverageAccuracy(split, percent_fields)