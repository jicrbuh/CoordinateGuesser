# from ogr import Geometry, wkbPoint
import osr, ogr, warnings

from .halfCorUnmanglers import *
from .unmanglerGenerator import *
from .normalize import fixdmschars
from .parse import Parse, decToDmsCoor
# from ..utilities import *
# from ..enc_detect import *
from .utilities import *
from .enc_detect import *

import csv, string
#from string import maketrans


def get_feature(layerPath, myField, myValue):
    dataSource = ogr.Open(layerPath, 0)
    layer = dataSource.GetLayer()
    spatialRef = layer.GetSpatialRef()
    #layerDefinition = layer.GetLayerDefn() #returns FeatureDefn object
    x, y = (None, None)

    for feature in layer:
        x, y = (None, None)
        #if (feature.GetField(myField) == myValue or feature.GetField(myField) == float(myValue)):
        if (feature.GetField(myField) == myValue):
            geom = feature.GetGeometryRef()
            (x, y) = ogrCoorTransform(geom.Centroid(), spatialRef)
            break
    return x, y


def parse_no_guess(input_pt, additional_pj=[]):
    output_guesses = Parse(input_pt, None, additional_pj)
    first_guess = output_guesses[0]
    output_pt, unmangler = first_guess[0], first_guess[1]
    distance = "no guess given"
    return output_pt, unmangler, distance


def parse_with_guess(input_pt, center_pt, additional_pj=[]):
    output_guesses = Parse(input_pt, center_pt, additional_pj)
    first_guess = output_guesses[0]
    output_pt, unmangler, distance = first_guess[0], first_guess[1], first_guess[2]
    return output_pt, unmangler, distance/1000


def parse_with_layer(input_pt, layer, field, value, additional_pj=[]):
    center_pt = get_feature(layer, field, value)
    output_guesses = Parse(input_pt, center_pt, additional_pj)
    first_guess = output_guesses[0]
    output_pt, unmangler, distance = first_guess[0], first_guess[1], first_guess[2]
    return output_pt, unmangler, distance/1000


def add_fields(layer):
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


def create_wkt_poly(pointlist):
    # POLYGON ((x1 y1, x2 y2, x1 y1))
    wkt = "POLYGON (("
    if len(pointlist) > 1:
        for point in pointlist:
            wkt = wkt + "{:f} {:f}, ".format(point[0], point[1])
        wkt = wkt + "{:f} {:f}".format(pointlist[0][0], pointlist[0][1]) #add first point again
    else:
        wkt = wkt + "{:f} {:f}, ".format(pointlist[0][0], pointlist[0][1])
        wkt = wkt + "{:f} {:f}".format(pointlist[0][0], pointlist[0][1])
    wkt = wkt + "))"
    return wkt


def setfields(feature, mangx, mangy, guessx, guessy, distance, method, pj, data):
    feature.SetField("Mangled X", mangx)
    feature.SetField("Mangled Y", mangy)
    feature.SetField("Guess X", guessx)
    feature.SetField("Guess Y", guessy)
    feature.SetField("distance", distance)
    feature.SetField("Method", method)
    feature.SetField("additional projection", pj)
    feature.SetField("Other Data", data)


def add_point_feature(layer, mangx, mangy, guessx, guessy, x, y, distance, method, pj, data=None):
    feature = ogr.Feature(layer.GetLayerDefn())
    # Set the attributes using the values from the delimited text file
    setfields(feature, mangx, mangy, guessx, guessy, distance, method, pj, data)

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


def create_data_source_shp(output_file):
    driver = ogr.GetDriverByName("ESRI Shapefile")
    shapepath = os.path.splitext(output_file)[0] + ".shp"
    if os.path.exists(shapepath):
        os.remove(shapepath)
    data_source = driver.CreateDataSource(shapepath)
    return data_source


def read_to_coord_list(input_file, usingfield):
    myencoding = get_encoding_by_bom(input_file)
    coordlist = []
    with open(input_file, newline='', encoding=myencoding) as csv_input:
        reader = csv.reader(csv_input, delimiter=',', quotechar='"')
        for i, row in enumerate(reader):
            if usingfield:
                coordelem = SingleCoord((row[0], row[1]), row[2])
                coordelem.data = row[3:]
            else:
                coordelem = SingleCoord((row[0], row[1]))
                coordelem.data = row[2:]
            # print(coordelem)
            coordlist.append(coordelem)
    return coordlist


def parse_coord_list(coordlist):
    for elem in coordlist:
        if elem.center_pt is None:  # if not using a guess for calculation
            try:
                print("no guess, input pt: {}".format(elem.input_pt))
                elem.output_pt, elem.unmangler, elem.distance = parse_no_guess(elem.input_pt)
                elem.distance = elem.distance/1000  # m to km
            except:
                elem.err = 1
        else:  # using a guess to parse the coordinate
            try:
                print("w guess, input pt: {}. guess: {}".format(elem.input_pt, elem.center_pt))
                elem.output_pt, elem.unmangler, elem.distance = parse_with_guess(elem.input_pt, elem.center_pt, elem.additional_pj)
            except:
                elem.err = 1
    return coordlist


def print_coordlist(coordlist):
    print("coordlist: ")
    for elem in coordlist:
        print(elem)
    print("end of coordlist")


def parse_file(input_file, guessx, guessy, fileformat, guesslayer=None, guessfield=None, additional_pj=[]):
    using_guess = guessy and guessx
    using_field = guesslayer and guessfield  # if there's layer and field then we use the third column
    coordlist = read_to_coord_list(input_file, using_field)

    if using_guess:
        center_pt = (guessx, guessy)
        for elem in coordlist:
            elem.center_pt = center_pt

    elif using_field:
        for elem in coordlist:
            elem.center_pt = get_feature(guesslayer, guessfield, elem.attr)

    coordlist = parse_coord_list(coordlist)

    # save to file (csv, point shapefile or polygon shapefile)
    if fileformat == 0:
        to_csv(input_file, coordlist)
    elif fileformat == 1:
        to_points(input_file, coordlist)
    elif fileformat == 2:
        to_poly(input_file, coordlist)


def in_path_to_out(input_path):
    return os.path.splitext(input_path)[0] + "_output"


def create_data_source(output_file):
    driver = ogr.GetDriverByName("ESRI Shapefile")
    if os.path.exists(output_file):
        os.remove(output_file)
    data_source = driver.CreateDataSource(output_file)
    return data_source


def group_coords(coordlist):
    """changes the elem.group to an integer so that
    all SingleCoor with the same elem.group (integer) will be in the same polygon"""
    for i in range(len(coordlist)):
        coord = coordlist[i]
        # if point is empty, or already in group continue to next point
        if (coord.input_pt is None) or (coord.group != 0):
            continue

        coord.group = i  # mark the group number
        for j in range(len(coordlist)):
            loopcoord = coordlist[j]
            # if both points have the same guess, set the group number to be the same
            if (coord.center_pt[0] == loopcoord.center_pt[0]) and (coord.center_pt[1] == loopcoord.center_pt[1]):
                loopcoord.group = i

    return coordlist


def add_poly_feature(layer, mangx, mangy, guessx, guessy, wkt, distance, method, pj, data=None):
    feature = ogr.Feature(layer.GetLayerDefn())
    # Set the attributes using the values from the delimited text file
    setfields(feature, mangx, mangy, guessx, guessy, distance, method, pj, data)
    # Create the point from the Well Known Txt
    poly = ogr.CreateGeometryFromWkt(wkt)
    # Set the feature geometry using the point
    feature.SetGeometry(poly)
    # Create the feature in the layer (shapefile)
    layer.CreateFeature(feature)
    # Destroy the feature to free resources
    feature.Destroy()


def to_poly(input_file, coordlist):
    output_file = in_path_to_out(input_file) + ".shp"
    data_source = create_data_source(output_file)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    shplayer = data_source.CreateLayer("UnmangledCoords", srs, ogr.wkbPolygon)
    add_fields(shplayer)

    usedlist = [0] * len(coordlist)
    coordlist = group_coords(coordlist)

    for i in range(len(coordlist)):
        elem = coordlist[i]
        # if a group already used for a poly, or coord is empty, continue
        if usedlist[i] or elem.output_pt is None:
            continue
        polylist = [(elem.output_pt[0], elem.output_pt[1])]
        usedlist[i] = 1

        # go over all coords and add them as polygons, grouped by their field group
        for j in range(len(coordlist)):
            loopcoord = coordlist[j]
            if (loopcoord.group == elem.group) and (usedlist[j] == 0):
                polylist.append((loopcoord.output_pt[0], loopcoord.output_pt[1]))
                usedlist[j] = 1

        # create the poly and add it to layer
        wkt = create_wkt_poly(polylist)
        add_poly_feature(shplayer, *elem.input_pt, *elem.center_pt, wkt, elem.distance,
                         elem.unmangler, " ", " ".join(elem.data))

    data_source.Destroy()


def to_points(input_file, coordlist):
    output_file = in_path_to_out(input_file) + ".shp"
    data_source = create_data_source(output_file)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    shplayer = data_source.CreateLayer("UnmangledCoords", srs, ogr.wkbPoint)
    add_fields(shplayer)
    for elem in coordlist:
        add_point_feature(shplayer, *elem.input_pt, *elem.center_pt, *elem.output_pt, elem.distance,
                          elem.unmangler, " ", " ".join(elem.data))
    data_source.Destroy()


def to_csv(input_file, coordlist):
    output_file = in_path_to_out(input_file) + ".csv"
    with open(output_file, 'w', newline='') as csv_output:
        writer = csv.writer(csv_output, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["mangled_X", "mangled_Y", "guess_X", "guess_Y", "unmangled_X",
                        "unmangled_Y", "distance_[km]", "method", "additional_pj", "other_data"])

        for i in range(len(coordlist)):
            elem = coordlist[i]
            if elem.err != 1:
                writer.writerow([*elem.input_pt, *elem.center_pt, *elem.output_pt, elem.distance,
                                elem.unmangler, elem.additional_pj, *elem.data])
                print("{}: {}, {}, {}".format(i, *elem.input_pt, elem.unmangler, elem.distance))
            else:
                writer.writerow(["error", "", "", "", "", "", "", "", "", *elem.data])
                print("{}: error". format(i))


#todo add https://pcjericks.github.io/py-gdalogr-cookbook/layers.html#create-a-new-shapefile-and-add-data
#todo documentation http://gdal.org/java/index.html?org/gdal/ogr/FieldDefn.html

class SingleCoord:
    def __init__(self, input_pt, attr=None, center_pt=None, output_pt=None, distance=None, unmangler=None,
                 additional_pj=[], data=None):
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

    def __str__(self):
        return "mangled: [{},{}], attr: {}".format(self.input_pt[0], self.input_pt[1], self.attr)

    def set_fields(self, feature):
        feature.SetField("Mangled X", self.input_pt[0])
        feature.SetField("Mangled Y", self.input_pt[1])
        feature.SetField("Guess X", self.center_pt[0])
        feature.SetField("Guess Y", self.center_pt[1])
        feature.SetField("distance", self.distance)
        feature.SetField("Method", self.unmangler)
        feature.SetField("additional projection", self.additional_pj)
        feature.SetField("Other Data", self.data)






