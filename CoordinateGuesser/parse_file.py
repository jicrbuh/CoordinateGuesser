# from ogr import Geometry, wkbPoint
import osr, ogr, warnings

from .halfCorUnmanglers import *
from .unmanglerGenerator import *
from .normalize import fixdmschars
from .parse import Parse, decToDmsCoor
#from ..utilities import *
#from ..enc_detect import *
from .utilities import *
from .enc_detect import *

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


def createWKTpoly(pointList): #todo maybe that's the problem 'MultiPolygon (((-74.1704 40.5546)))'
    # POLYGON ((x1 y1, x2 y2, x1 y1))
    wkb = "POLYGON (("
    if len(pointList) > 1:
        for point in pointList:
            wkb = wkb + "{:f} {:f}, ".format(point[0], point[1])
        wkb = wkb + "{:f} {:f}".format(pointList[0][0], pointList[0][1]) #add first point again
    else:
        wkb = wkb + "{:f} {:f}, ".format(pointList[0][0], pointList[0][1])
        wkb = wkb + "{:f} {:f}".format(pointList[0][0], pointList[0][1])
    wkb = wkb + "))"
    return wkb

def setFields(feature, mangx, mangy, guessx, guessy, distance,method, pj, data):
    feature.SetField("Mangled X", mangx)
    feature.SetField("Mangled Y", mangy)
    feature.SetField("Guess X", guessx)
    feature.SetField("Guess Y", guessy)
    feature.SetField("distance", distance)
    feature.SetField("Method", method)
    feature.SetField("additional projection", pj)
    feature.SetField("Other Data", data)


def addFeature(layer, mangx, mangy, guessx, guessy, x,y, distance,method, pj, data=None):

    feature = ogr.Feature(layer.GetLayerDefn())
    # Set the attributes using the values from the delimited text file
    setFields(feature,mangx, mangy, guessx, guessy, distance, method, pj, data)

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

def createDataSourceShp(output_file):
    driver = ogr.GetDriverByName("ESRI Shapefile")
    shapepath = os.path.splitext(output_file)[0] + ".shp"
    if os.path.exists(shapepath):
        os.remove(shapepath)
    data_source = driver.CreateDataSource(shapepath)
    return data_source


def readFileIntoList(input_file):
    rowslist = []
    with open(input_file) as csv_input:
        reader = csv.reader(csv_input, delimiter=',', quotechar='|')
        rowslist = list(reader)  # a list of lists. each list contains one row
    return rowslist

# https://gis.stackexchange.com/questions/92754/how-can-i-group-points-to-make-polygon-via-python
# https://gis.stackexchange.com/questions/254444/deleting-selected-features-from-vector-ogr-in-gdal-python
def createPolyFile(input_file, output_file):
    rowslist = readFileIntoList(input_file)
    data_source = createDataSourceShp(output_file)

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    shplayer = data_source.CreateLayer("UnmangledCoords", srs, ogr.wkbPolygon)
    addFields(shplayer)

    polyList = []
    usedList = [0]*len(rowslist)

    for i in range(len(rowslist)):
        row = rowslist[i]
        # if point is used, empty or header, break
        if usedList[i] or row[0] == "" or i == 0:
            continue
        usedList[i] = 1

        polyList = [(float(row[4]), float(row[5]))]
        # create feature
        feature = ogr.Feature(shplayer.GetLayerDefn())
        # add point data
        setFields(feature, row[0], row[1], row[2], row[3], row[6], row[7], row[8], None)

        for j in range(len(rowslist)):
            innerRow = rowslist[j]
            # if point is already in a polygon, skip it
            if usedList[j]:
                continue
            # if both points have the same guess, add to polygon and mark as used
            if (row[2] == innerRow[2]) and (row[3] == innerRow[3]):
                usedList[j] = 1
                polyList.append((float(innerRow[4]), float(innerRow[5])))

        # Set the feature geometry
        geom = ogr.CreateGeometryFromWkt(createWKTpoly(polyList))
        feature.SetGeometry(geom)
        shplayer.CreateFeature(feature)
        feature.Destroy()
    data_source.Destroy()


def read_to_coord_list(input_file, usingField):
    myencoding = get_encoding_by_bom(input_file)
    coordlist = []
    with open(input_file, newline='', encoding=myencoding) as csv_input:
        reader = csv.reader(csv_input, delimiter=',', quotechar='"')
        for i, row in enumerate(reader):
            if usingField:
                coordelem = SingleCoord((row[0], row[1]), row[2])
                coordelem.data = row[3:]
            else:
                coordelem = SingleCoord((row[0], row[1]))
                coordelem.data = row[2:]
            coordlist.append(coordelem)
    return coordlist


def parse_coord_list(coordlist):
    for elem in coordlist:
        if elem.center_pt is not None:  # if using guess for calculation
            try:
                elem.output_pt, elem.unmangler, elem.distance = parseNoGuess(elem.input_pt)
                elem.distance = elem.distance/1000  # m to km
            except:
                elem.err = 1
        else:
            try:
                elem.output_pt, elem.unmangler, elem.distance = parseWithGuess(elem.input_pt, elem.center_pt, elem.additional_pj)
            except:
                elem.err = 1
    return coordlist


def parse_file(input_file, guessX, guessY, tofile, guesslayer=None, guessfield=None, additional_pj=[]):

    usingGuess = guessY and guessX
    usingField = guesslayer and guessfield  # if there's layer and field then we use the third column
    coordlist = read_to_coord_list(input_file, usingField)

    if usingGuess:
        center_pt = (guessX, guessY)
        for elem in coordlist:
            elem.center_pt = center_pt

    elif usingField:
        for elem in coordlist:
            elem.center_pt = getFeature(guesslayer, guessfield, elem.attr)

    coordlist = parse_coord_list(coordlist)
    # save to file (csv, point shapefile or polygon shapefile)
    if tofile == 1:
        to_csv(input_file, coordlist)
    elif tofile == 2:
        to_points(input_file, coordlist)
    elif tofile == 3:
        to_poly(input_file, coordlist)


def in_path_to_out(input_path):
    return os.path.splitext(input_path)[0] + "_output"


def to_points(input_file, coordlist):
    output_file = in_path_to_out(input_file) + ".shp"


def to_poly(input_file, coordlist):
    output_file = in_path_to_out(input_file) + ".shp"
    


def to_csv(input_file, coordlist):
    output_file = in_path_to_out(input_file) + ".csv"
    with open(output_file, 'w', newline='') as csv_output:
        writer = csv.writer(csv_output, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["mangled_X", "mangled_Y", "guess_X", "guess_Y", "unmangled_X",
                        "unmangled_Y", "distance_[km]", "method", "additional_pj", "other_data"])

        for i, elem in coordlist:
            if elem.err != 1:
                writer.writerow([*elem.input_pt, *elem.center_pt, *elem.output_pt, elem.distance,
                                elem.unmangler, elem.additional_pj, *elem.data])
                print("{}: {}, {}, {}".format(i, *elem.input_pt, elem.unmangler, elem.distance))
            else:
                writer.writerow(["error", "", "", "", "", "", "", "", "", *elem.data])
                print("{}: error". format(i))


#todo add https://pcjericks.github.io/py-gdalogr-cookbook/layers.html#create-a-new-shapefile-and-add-data
#todo documentation http://gdal.org/java/index.html?org/gdal/ogr/FieldDefn.html
def parseFileNoCol(input_file, output_file, guessX, guessY, layer=None, field=None, additional_pj=[]):
    myencoding = get_encoding_by_bom(input_file)
    with open(input_file, newline='', encoding=myencoding) as csv_input, open(output_file, 'w', newline='') as csv_output:
        reader = csv.reader(csv_input, delimiter=',', quotechar='"')
        writer = csv.writer(csv_output, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)

        # set up the shapefile driver
        data_source = createDataSourceShp(output_file)

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        shplayer = data_source.CreateLayer("UnmangledCoords", srs, ogr.wkbPoint)
        addFields(shplayer)

        writer.writerow(["mangled_X", "mangled_Y", "guess_X", "guess_Y", "unmangled_X",
                         "unmangled_Y", "distance_[km]", "method","additional_pj","other_data"])
        center_pt = ("", "")
        usingGuess = guessY and guessX
        if usingGuess:
            center_pt = (guessX, guessY)
        # if there's layer and field then we use the third column
        usingField = layer and field

        for i, row in enumerate(reader):  # i is the index of the row

            #try:

            input_pt = (row[0], row[1])
            if usingGuess:
                output_pt, unmangler, distance= parseWithGuess(input_pt,(guessX,guessY),additional_pj)
                distance = distance/1000
            elif usingField:
                attr = row[2]
                center_pt = getFeature(layer, field, attr)
                output_pt, unmangler, distance = parseWithGuess(input_pt, center_pt, additional_pj)
                distance = distance / 1000
            else:
                output_pt, unmangler, distance = parseNoGuess(input_pt)

            if usingField:
                writer.writerow([*input_pt, *center_pt, *output_pt, distance, unmangler,additional_pj, *row[3:]])
                addFeature(shplayer, *input_pt, *center_pt, *output_pt, distance, unmangler, " "," ".join(row[3:]))
            else:
                writer.writerow([*input_pt, *center_pt, *output_pt, distance, unmangler,additional_pj, *row[2:]])
                addFeature(shplayer, *input_pt, *center_pt, *output_pt, distance, unmangler, " ", " ".join(row[2:]))

            print("{}: {}, {}, {}".format(i, *output_pt, unmangler, distance))
            #except:
                #writer.writerow(["error","","","","","","","","",*row])

        data_source.Destroy()

    createPolyFile(output_file, output_file)


class SingleCoord:
    def __init__(self, input_pt, attr=None, center_pt=None, output_pt=None, distance=None, unmangler=None, additional_pj=None, data=None):
        self.input_pt = input_pt
        self.attr = attr
        self.center_pt = center_pt
        self.output_pt = output_pt
        self.distance = distance
        self.unmangler = unmangler
        self.additional_pj = additional_pj
        self.data = data
        self.group = 0
        self.err = 0

    def write_coord(self, mywriter):
        pass

    def parse_coord(self):
        pass

    def set_fields(self, feature):
        feature.SetField("Mangled X", self.input_pt[0])
        feature.SetField("Mangled Y", self.input_pt[1])
        feature.SetField("Guess X", self.center_pt[0])
        feature.SetField("Guess Y", self.center_pt[1])
        feature.SetField("distance", self.distance)
        feature.SetField("Method", self.unmangler)
        feature.SetField("additional projection", self.additional_pj)
        feature.SetField("Other Data", self.data)

    def parse_with_guess(self):
        output_guesses = Parse(self.input_pt, self.center_pt, self.additional_pj)
        first_guess = output_guesses[0]
        self.output_pt = first_guess[0]
        self.unmangler = first_guess[1]
        self.distance = first_guess[2]/1000

    def parse_no_guess(self):
        output_guesses = Parse( input_pt, None, additional_pj)
        first_guess = output_guesses[0]
        output_pt, unmangler = first_guess[0], first_guess[1]
        distance = "no guess given"
        return output_pt, unmangler, distance

    def parse_with_layer(self, layer, field, value):
        self.center_pt = getFeature(layer, field, value)
        self.parse_with_guess()


    class Attr:
        def __init__(self, value, name):
            self.value = value
            self.name = name



