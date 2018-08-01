# from ogr import Geometry, wkbPoint
import osr, ogr, warnings

from .halfCorUnmanglers import *
from .unmanglerGenerator import *
from .normalize import fixdmschars
from .parse import Parse, decToDmsCoor
from ..utilities import *
from ..enc_detect import *
import csv, string
#from string import maketrans


def getFeature(layerPath, myField, myValue):
    dataSource = ogr.Open(layerPath, 0)
    layer = dataSource.GetLayer()
    spatialRef = layer.GetSpatialRef()
    #layerDefinition = layer.GetLayerDefn() #returns FeatureDefn object
    x,y = (None,None)

    for feature in layer:
        #print(myValue + " " + feature.GetField(myField))
        #if (feature.GetField(myField) == myValue or feature.GetField(myField) == float(myValue)):
        if (feature.GetField(myField) == myValue):
            geom = feature.GetGeometryRef()
            (x, y) = ogrCoorTransform(geom.Centroid(), spatialRef)
            break
    return (x,y)

def parseNoGuess(input_pt, additional_pj=[]):
    output_guesses = Parse(input_pt, None, additional_pj)
    first_guess = output_guesses[0]
    output_pt, unmangler = first_guess[0], first_guess[1]
    distance = "no guess given"
    return (output_pt, unmangler, distance)

def parseWithGuess(input_pt, center_pt, additional_pj=[]):
    output_guesses = Parse(input_pt, center_pt, additional_pj)
    first_guess = output_guesses[0]
    output_pt, unmangler, distance = first_guess[0], first_guess[1], first_guess[2]
    return (output_pt, unmangler, distance)


def parseWithLayer(input_pt, layer, field, value, additional_pj=[]):

    center_pt = getFeature(layer,field,value)
    output_guesses = Parse(input_pt, center_pt, additional_pj)
    first_guess = output_guesses[0]
    output_pt, unmangler, distance = first_guess[0], first_guess[1], first_guess[2]
    return (output_pt, unmangler, distance)

def addFields(layer):
    field_mangledx = ogr.FieldDefn("Mangled X", ogr.OFTString)
    field_mangledx.SetWidth(24)
    layer.CreateField(field_mangledx)
    field_mangledy = ogr.FieldDefn("Mangled Y", ogr.OFTString)
    field_mangledy.SetWidth(24)
    layer.CreateField(field_mangledy)
    layer.CreateField(ogr.FieldDefn("Guess X", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("Guess Y", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("distance", ogr.OFTReal))
    field_method = ogr.FieldDefn("Method", ogr.OFTString)
    field_method.SetWidth(24)
    layer.CreateField(field_method)
    field_pj = ogr.FieldDefn("additional projection", ogr.OFTString)
    field_pj.SetWidth(24)
    layer.CreateField(field_pj)
    field_data = ogr.FieldDefn("Other Data", ogr.OFTString)
    field_data.SetWidth(48)
    layer.CreateField(field_data)


def createWKBpoly(pointList):
    # POLYGON ((x1 y1, x2 y2, x1 y1))
    wkb = "POLYGON (("
    for point in pointList:
        wkb = wkb + "{:f} {:f}".format(point[0], point[1])
    wkb = wkb + "))"
    return wkb



def addFeature(layer, mangx, mangy, guessx, guessy, x,y, distance,method, pj, data=None):

    feature = ogr.Feature(layer.GetLayerDefn())
    # Set the attributes using the values from the delimited text file
    feature.SetField("Mangled X", mangx)
    feature.SetField("Mangled Y", mangy)
    feature.SetField("Guess X", guessx)
    feature.SetField("Guess Y", guessy)
    feature.SetField("distance", distance)
    feature.SetField("Method", method)
    feature.SetField("additional projection", pj)
    feature.SetField("Other Data", data)

    # create the WKT for the feature using Python string formatting
    wkt = "POINT({:f} {:f})".format(x, y)

    # Create the point from the Well Known Txt
    point = ogr.CreateGeometryFromWkt(wkt)

    # Set the feature geometry using the point
    feature.SetGeometry(point)
    # Create the feature in the layer (shapefile)
    layer.CreateFeature(feature)
    # Destroy the feature to free resources
    feature.Destroy()


# https://gis.stackexchange.com/questions/92754/how-can-i-group-points-to-make-polygon-via-python
# https://gis.stackexchange.com/questions/254444/deleting-selected-features-from-vector-ogr-in-gdal-python

def createPolyFile(input_file, output_file):
    rowslist =[]
    myencoding = get_encoding_by_bom(input_file)
    with open(input_file, newline='', encoding=myencoding) as csv_input:
        reader = csv.reader(csv_input, delimiter=',', quotechar='"')
        rowslist = list(reader) #a list of lists. each list contains one row

    driver = ogr.GetDriverByName("ESRI Shapefile")
    shapepath = os.path.splitext(output_file)[0] + ".shp"
    if os.path.exists(shapepath):
        os.remove(shapepath)
    data_source = driver.CreateDataSource(shapepath)

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    shplayer = data_source.CreateLayer("UnmangledCoords", srs, ogr.wkbPolygon)
    addFields(shplayer)

    usedList = [0]*len(rowslist)

    for i in range(len(rowslist)):
        row = rowslist[i]

        #if point is used, empty or header, break
        if (usedList[i] or row[0] == "" or i==0):
            break
        usedList[i] = 1
        ring = ogr.Geometry(ogr.wkbLinearRing) # create ring
        firstPoint = (float(row[4]), float(row[5])) # save  coordinates. why?

        # add point data

        for j in range(len(rowslist)):
            innerRow = rowslist[j]
            # if point is already in a polygon, skip it
            if usedList[j]:
                break
            # if both points have the same guess, add to polygon and mark as used
            if (row[2] == innerRow[2]) and (row[3] == innerRow[3]):
                ring.AddPoint(float(innerRow[4]), float(innerRow[5]))
                usedList[j] = 1

        # Add first point again to ring to close polygon
        ring.AddPoint(float(row[4]), float(row[5]))


        #create feature

        # Set the feature geometry using the point
        feature.SetGeometry(ring)



#todo add https://pcjericks.github.io/py-gdalogr-cookbook/layers.html#create-a-new-shapefile-and-add-data
#todo documentation http://gdal.org/java/index.html?org/gdal/ogr/FieldDefn.html
def parseFileNoCol(input_file, output_file, guessX, guessY, layer=None, field=None, additional_pj=[]):
    myencoding = get_encoding_by_bom(input_file)
    with open(input_file, newline='', encoding=myencoding) as csv_input, open(output_file, 'w', newline='') as csv_output:
        reader = csv.reader(csv_input, delimiter=',', quotechar='"')
        writer = csv.writer(csv_output, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        # set up the shapefile driver
        driver = ogr.GetDriverByName("ESRI Shapefile")
        shapepath = os.path.splitext(output_file)[0]+".shp"
        if os.path.exists(shapepath):
            os.remove(shapepath)
        data_source = driver.CreateDataSource(shapepath)

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        shplayer = data_source.CreateLayer("UnmangledCoords", srs, ogr.wkbPoint)
        addFields(shplayer)

        writer.writerow(["mangled X", "mangled Y", "guess X", "guess Y", "unmangled X",
                         "unmangled Y", "distance [km]", "method","additional_pj","other data from file"])
        center_pt = ("", "")
        usingGuess = guessY and guessX
        if usingGuess:
            center_pt = (guessX,guessY)
        # if there's layer and field then we use the third column
        usingField = layer and field

        for i,row in enumerate(reader): # i is the index of the row

            #try:

            input_pt = (row[0], row[1])

            if usingGuess:
                output_pt, unmangler, distance= parseWithGuess(input_pt,(guessX,guessY),additional_pj)
            elif usingField:
                attr = row[2]
                center_pt = getFeature(layer,field,attr)
                output_pt, unmangler, distance = parseWithGuess(input_pt, center_pt, additional_pj)
            else:
                output_pt, unmangler, distance = parseNoGuess(input_pt)

            if usingField:
                writer.writerow([*input_pt, *center_pt, *output_pt, distance/1000, unmangler,additional_pj, *row[3:]])
                addFeature(shplayer, *input_pt,*center_pt, *output_pt, distance/1000, unmangler, " "," ".join(row[3:]))
            else:
                writer.writerow([*input_pt, *center_pt, *output_pt, distance/1000, unmangler,additional_pj, *row[2:]])
                addFeature(shplayer, *input_pt, *center_pt, *output_pt, distance/1000, unmangler, " ", " ".join(row[2:]))

            print("{}: {}, {}, {}".format(i, *output_pt, unmangler, distance/1000))
            #except:
                #writer.writerow(["error","","","","","","","","",*row])

        data_source.Destroy()

