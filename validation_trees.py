import arcpy
from arcpy import env
from arcpy.sa import *
import numpy as np
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

    split = [e.split(', ') for e in lines]

    [split] = split

    split[-1] = (split[-1])[:-2]

    split.pop(0)

    split = [x.lower() for x in split]

    return split

def getDominantClass(INPUT_CLASSIFICATION, VAL_DATA):
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
    arcpy.management.CalculateField("TabArea_layer", "px_total", "" "!" + '!+!'.join(values_list) + "!" "", "PYTHON3")

    # create fields for storing the percentage of pixels
    for druh in split:
        arcpy.AddField_management("TabArea_layer", f"{druh}_pc", "DOUBLE")

    # calculate the proportions
    zipped = list(zip(split, values_list))
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

    # determining which class is dominant in validation polygon
    max_druh_list = []
    cursor = arcpy.da.SearchCursor("validated.shp", percent_fields[:-1])
    for row in cursor:

        max_pc = max(row)
        max_pc_idx = row.index(max_pc)

        if max_pc > 0:
            max_druh = split[max_pc_idx]
            max_druh_list.append(max_druh)

        # if maximal proportion is 0, then whole validation polygon consists of Masked pixels and the dominant class is non-existent
        else:
            max_druh_list.append("None")

    del cursor

    # add field where the name of a dominant class will be stored
    arcpy.AddField_management("validated.shp", "dominant", "Text")

    # insert dominant class into created field
    pointer = 0
    with arcpy.da.UpdateCursor("validated.shp", 'dominant') as cursor:
         for row in cursor:
             row[0] = max_druh_list[pointer]
             cursor.updateRow(row)

             pointer += 1

    # add another field which will determine if correct or incorrect class is dominant within validation polygon
    arcpy.AddField_management("validated.shp", "correct", "Short")

    with arcpy.da.UpdateCursor("validated.shp", ['classname', 'dominant', 'correct']) as cursor:

        for row in cursor:

            # if validation polygon classname == dominant class within validation polygon, insert 1
            if str(row[0]).lower() == str(row[1]).lower():
                row[2] = 1
                cursor.updateRow(row)

            # no dominant class within validation polygon (contains just Masked pixels), insert -1
            elif str(row[1]) == 'None':
                row[2] = -1
                cursor.updateRow(row)

            # wrong class is dominant, insert 0
            else:
                row[2] = 0
                cursor.updateRow(row)

        return split

def confusionMatrix(split):

    # create a matrix
    conf_matrix = np.zeros((len(split) - 1, len(split) - 1))

    # generating confusion matrix
    with arcpy.da.SearchCursor("validated.shp", ['classname', 'dominant', 'correct']) as cursor:

        # loop through every validation polygon
        for row in cursor:

            for idx, druh in enumerate(split[:-1]):

                # if class of validation polygon == dominant class within validation polygon
                if (str(row[0]).lower() == druh) and (str(row[1]).lower() == druh):

                    # add +1 on a main diagonal
                    conf_matrix[idx][idx] += 1

                # if class of validation polygon != dominant class within validation polygon and the dominant class exists (is not None)
                elif (str(row[0]).lower() == druh) and (str(row[1]).lower() != druh) and str(row[1]) != 'None':

                    # determine which class is dominant
                    druh_r1 = str(row[1])
                    idx_druh_r1 = split.index(druh_r1)

                    # add +1 to a relevant matrix field
                    conf_matrix[idx_druh_r1][idx] += 1

    print("VALIDACNE STROMY")
    print(split[:-1])
    print(conf_matrix)

    # computing producer and user accuracy
    sumy1 = []
    hd = []

    for s in range(len(split) - 1):

        sum = 0
        hd.append(conf_matrix[s][s])

        for r in range(len(split) - 1):
            sum += conf_matrix[r][s]

        sumy1.append(sum)

    print(f'{sumy1} total')


    sumy2 = []
    for r in range(len(split) - 1):

        sum = 0

        for s in range(len(split) - 1):
            sum += conf_matrix[r][s]

        sumy2.append(sum)

    sprac_pres = []
    uziv_pres = []
    for i in range(len(sumy1)):
        if hd[i] == 0:
            sprac_pres.append(0)
            uziv_pres.append(0)
        else:
            sprac_pres.append(round((hd[i] / sumy1[i])*100, 2))
            uziv_pres.append(round((hd[i] / sumy2[i])*100, 2))

    zipped = dict(zip(split[:-1], sprac_pres))
    print("SPRACOVATELSKA PRESNOST:")
    print(zipped)

    zipped = dict(zip(split[:-1], uziv_pres))
    print("UZIVATELSKA PRESNOST:")
    print(zipped)

    # computing F1-score of producer and user accuracy
    f1 = []
    for i in range(len(sprac_pres)):
        if sprac_pres[i] == 0:
            f1.append(0)
        else:
            f1skore = round(2 * (uziv_pres[i] * sprac_pres[i])/(uziv_pres[i] + sprac_pres[i]), 2)
            f1.append(f1skore)

    zipped = dict(zip(split[:-1], f1))
    print("F1 SKORE:")
    print(zipped)

    sum_hd = np.sum(hd)
    sum_sumy1 = np.sum(sumy1)
    sum_sumy2 = np.sum(sumy2)

    # computing overall accuracy
    eps = 1.0e-10
    if sum_sumy1 == sum_sumy2 or (abs(sum_sumy1 - sum_sumy2) < eps):
        celk_pres = round((sum_hd / sum_sumy1)*100, 2)
        print("CELKOVA PRESNOST:")
        print(celk_pres)
    else:
        print("Chyba vo vypocte matice!")

    arcpy.Delete_management("validated.shp")

#### INPUTS ####

# classification to validate (DAT format)
INPUT_CLASSIFICATION = r'E:\classification.dat'

# validation polygons
VAL_DATA = r'E:\validation_polygons.shp'

################


#### SCRIPT ####
arcpy.env.workspace = os.path.dirname(INPUT_CLASSIFICATION)
arcpy.env.overwriteOutput = 1
arcpy.env.qualifiedFieldNames = 0

classes = getDominantClass(INPUT_CLASSIFICATION, VAL_DATA)
confusionMatrix(classes)