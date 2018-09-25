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


def add_string_fields(layer, fieldlist):
    for myfield in fieldlist:
        field_data = ogr.FieldDefn(myfield, ogr.OFTString)
        field_data.SetWidth(48)
        layer.CreateField(field_data)


def add_fields(layer, fieldlist):
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

    field_pj = ogr.FieldDefn("add. proj", ogr.OFTString)
    field_pj.SetWidth(300)
    layer.CreateField(field_pj)

    field_data = ogr.FieldDefn("Other Data", ogr.OFTString)
    field_data.SetWidth(48)
    layer.CreateField(field_data)
    add_string_fields(layer, fieldlist)


def set_data_fields(coordlist, feature, elem):
    """ adding the other data to the feature.
    if there are more data elements than available fields, we join them and add them under "Other Data".
    if headers =[] then len(headers) = 0
    """
    headers = coordlist[0]
    for i, data_i in enumerate(elem.data):
        if i < len(headers):
            feature.SetField(headers[i], data_i)
        else:
            feature.SetField("Other Data", "; ".join(elem.data[i:]))
            break


def setfields(feature, mangx, mangy, guessx, guessy, distance, method, pj):
    #print("got into setfields")
    feature.SetField("Mangled X", mangx)
    feature.SetField("Mangled Y", mangy)
    if guessx:
        feature.SetField("Guess X", guessx)
    if guessy:
        feature.SetField("Guess Y", guessy)
    if distance:
        feature.SetField("distance", distance)
    feature.SetField("Method", method)
    if pj == []:
        #print("pj is []")
        feature.SetField("add. proj", "")
    else:
        #print(f"pj is {pj}")
        feature.SetField("add. proj", ';'.join(pj))


def add_point_feature(layer, elem, coordlist):
    if elem.err == 1:
        return
    feature = ogr.Feature(layer.GetLayerDefn())

    # Set the attributes using the values from elem
    setfields(feature, elem.input_pt[0], elem.input_pt[1], elem.center_pt[0], elem.center_pt[1],
              elem.distance, elem.unmangler, elem.additional_pj)

    # set the additional data field
    set_data_fields(coordlist, feature, elem)
    # create the WKT for the feature using Python string formatting
    wkt = "POINT({:f} {:f})".format(elem.output_pt[0], elem.output_pt[1])
    # Create the point from the Well Known Txt
    point = ogr.CreateGeometryFromWkt(wkt)
    # Set the feature geometry using the point
    feature.SetGeometry(point)
    # Create the feature in the layer (shapefile)
    layer.CreateFeature(feature)
    # Destroy the feature to free resources
    feature.Destroy()


def read_using_field(coordlist, reader, header, additional_pj):
    lastgroup = 0
    lastattr = None
    for i, row in enumerate(reader):
        if i == 0:
            if header:
                if row and len(row) > 3:
                    coordlist.append(row[3:])
                    continue
                else:
                    coordlist.append([])
                    continue
            else:
                coordlist.append([])
        if row:
            if row[2] != lastattr:  # if the attribute is different from the last coord's attribute
                lastgroup = lastgroup + 1

            coordelem = SingleCoord((row[0], row[1]), row[2])
            coordelem.additional_pj = additional_pj
            if row[3:] is not None:  # if there is other data to save
                coordelem.data = row[3:]
            else:
                coordelem.data = []

            lastattr = row[2]
            coordelem.group = lastgroup
            coordlist.append(coordelem)

        else:
            lastattr = None
            lastgroup = lastgroup + 1


def read_no_guess_field(coordlist, reader, header, additional_pj):
    lastgroup = 0
    for i, row in enumerate(reader):
        if i == 0:
            if header:
                if row and len(row) > 2:
                    coordlist.append(row[2:])
                    continue
                else:
                    coordlist.append([])
                    continue
            else:
                coordlist.append([])

        if row:
            coordelem = SingleCoord((row[0], row[1]))
            coordelem.group = lastgroup
            lastgroup = lastgroup + 1
            if row[2:] is not None:
                coordelem.data = row[2:]
            else:
                coordelem.data = []
            coordelem.additional_pj = additional_pj
            coordlist.append(coordelem)


def read_using_guess(coordlist, reader, header, additional_pj):
    for i, row in enumerate(reader):
        if i == 0:
            if header:
                if row and len(row) > 2:
                    coordlist.append(row[2:])
                    continue
                else:
                    coordlist.append([])
                    continue
            else:
                coordlist.append([])
        if row:
            coordelem = SingleCoord((row[0], row[1]))
            if row[2:] is not None:
                coordelem.data = row[2:]
            else:
                coordelem.data = []
            coordelem.additional_pj = additional_pj
            coordlist.append(coordelem)


def read_to_coord_list(input_file, using_field, using_guess, header, additional_pj):
    myencoding = get_encoding_by_bom(input_file)
    # print("encoding: {}".format(myencoding))
    coordlist = []
    with open(input_file, newline='', encoding=myencoding) as csv_input:
        reader = csv.reader(csv_input, delimiter=',', quotechar='"')

        if using_field:     # if using field, need to group according to row[2]
            read_using_field(coordlist, reader, header, additional_pj)

        elif using_guess:   # if using guess - all coords in same group.
            read_using_guess(coordlist, reader, header, additional_pj)

        else:               # if not using a guess - each in new group
            read_no_guess_field(coordlist, reader, header, additional_pj)

    return coordlist


def parse_coord_list(coordlist):
    for elem in coordlist:
        if isinstance(elem, list):
            continue
        if elem.center_pt[0] is "":  # if not using a guess for calculation
            try:
                print("no guess, input pt: {}".format(elem.input_pt))
                elem.output_pt, elem.unmangler, elem.distance = parse_no_guess(elem.input_pt, elem.additional_pj)
            except:
                print("err for input pt: {}".format(elem.input_pt))
                elem.err = 1
        else:  # using a guess to parse the coordinate
            try:
                print("w guess, input pt: {}. guess: {}".format(elem.input_pt, elem.center_pt))
                elem.output_pt, elem.unmangler, elem.distance = parse_with_guess(elem.input_pt, elem.center_pt, elem.additional_pj)
            except:
                print("err for input pt: {}".format(elem.input_pt))
                elem.err = 1
    return coordlist


def parsefile(input_file, guessx, guessy, fileformat, header, guesslayer=None, guessfield=None, additional_pj=[]):
    if guessy and guessx:
        using_guess = True
    else:
        using_guess = False
    print("using guess: {}".format(using_guess))
    if guesslayer and guessfield:
        using_field = True
    else:
        using_field = False
    print("using_fields: {}".format(using_field))
    # coordlist structure:
    #   if header       [[header1, header2],SingleCoord1,SingleCoord2,SingleCoord3]
    #   if not header   [[],SingleCoord1,SingleCoord2,SingleCoord3]
    coordlist = read_to_coord_list(input_file, using_field, using_guess, header, additional_pj)
    print("coordlist[0]: {}".format(coordlist[0]))
    # if there is a header, for csv, append the row written to the head of the other.data list and print
    if using_guess:
        center_pt = (guessx, guessy)
        for elem in coordlist:
            if isinstance(elem, list):
                continue
            elem.center_pt = center_pt

    elif using_field:
        for elem in coordlist:
            if isinstance(elem, list):
                continue
            elem.center_pt = get_feature(guesslayer, guessfield, elem.attr)

    coordlist = parse_coord_list(coordlist)

    # save to file (csv, point shapefile or polygon shapefile)
    if fileformat == 0:
        return to_csv(input_file, coordlist)
    elif fileformat == 1:
        return to_points(input_file, coordlist)
    elif fileformat == 2:
        return to_poly(input_file, coordlist)


def add_poly_feature(layer, elem, coordlist, wkt):
    feature = ogr.Feature(layer.GetLayerDefn())
    # Set the attributes using the values from the delimited text file
    setfields(feature, elem.input_pt[0], elem.input_pt[1], elem.center_pt[0], elem.center_pt[1],
              elem.distance, elem.unmangler, elem.additional_pj)
    # set the additional data field
    set_data_fields(coordlist, feature, elem)
    # Create the point from the Well Known Txt
    poly = ogr.CreateGeometryFromWkt(wkt)
    # Set the feature geometry using the point
    feature.SetGeometry(poly)
    # Create the feature in the layer (shapefile)
    layer.CreateFeature(feature)
    # Destroy the feature to free resources
    feature.Destroy()


def to_poly(input_file, coordlist):

    output_file = in_path_to_dir(input_file) + "_polygon_output.shp"
    data_source = create_data_source(output_file)
    try:
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        shplayer = data_source.CreateLayer("UnmangledCoords", srs, ogr.wkbPolygon)

        add_fields(shplayer, coordlist[0])  # adds the fields to the output shapefile

        usedlist = [0] * len(coordlist)
        usedlist[0] = 1
        for i in range(len(coordlist)):

            elem = coordlist[i]

            # skip element if it's erroneous or used
            if usedlist[i] == 1 or elem.err == 1:
                continue
            usedlist[i] = 1
            polylist = [(elem.output_pt[0], elem.output_pt[1])]

            for j in range(len(coordlist)):
                innerelem = coordlist[j]
                # if already used element, skip to next j
                if usedlist[j] == 1:
                    continue
                # if got to a different group (different polygon), get out of j loop
                if innerelem.group != elem.group:
                    break

                polylist.append((innerelem.output_pt[0], innerelem.output_pt[1]))
                usedlist[j] = 1

            # create the poly and add it to layer
            wkt = create_wkt_poly(polylist)
            add_poly_feature(shplayer, elem, coordlist, wkt)

    finally:
        data_source.Destroy()
    return output_file


def to_points(input_file, coordlist):
    output_file = in_path_to_dir(input_file) + "_point_output.shp"
    data_source = create_data_source(output_file)
    try:
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        shplayer = data_source.CreateLayer("UnmangledCoords", srs, ogr.wkbPoint)
        add_fields(shplayer, coordlist[0])

        for i, elem in enumerate(coordlist):
            if i == 0:
                continue
            add_point_feature(shplayer, elem, coordlist)
    finally:
        data_source.Destroy()
    return output_file


def to_csv(input_file, coordlist):
    output_file = in_path_to_out(input_file) + ".csv"
    with open(output_file, 'w', newline='') as csv_output:
        writer = csv.writer(csv_output, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)

        if coordlist[0] == []:  # if using a header, the basic header won't includ "other data"
            myheader = ["mangled_X", "mangled_Y", "guess_X", "guess_Y", "unmangled_X",
                        "unmangled_Y", "distance_[km]", "method", "additional_pj", "other_data"]
        else:
            myheader = ["mangled_X", "mangled_Y", "guess_X", "guess_Y", "unmangled_X",
                        "unmangled_Y", "distance_[km]", "method", "additional_pj"]

        myheader = myheader + coordlist[0]

        writer.writerow(myheader)

        for i in range(len(coordlist)):
            if i == 0:
                continue
            elem = coordlist[i]
            if elem.err != 1:
                writer.writerow([*elem.input_pt, *elem.center_pt, *elem.output_pt, elem.distance,
                                elem.unmangler, elem.additional_pj, *elem.data])

                print("{}: {}, {}, {}".format(i, *elem.input_pt, elem.unmangler, elem.distance))
            else:
                writer.writerow(["error", "", "", "", "", "", "", "", "", *elem.data])
                print("{}: error". format(i))
    return output_file


def in_path_to_out(input_path):
    return os.path.splitext(input_path)[0] + "_output"


def in_path_to_dir(input_path):
    return os.path.splitext(input_path)[0]


def create_data_source_shp(output_file):
    driver = ogr.GetDriverByName("ESRI Shapefile")
    shapepath = os.path.splitext(output_file)[0] + ".shp"
    if os.path.exists(shapepath):
        os.remove(shapepath)
    data_source = driver.CreateDataSource(shapepath)
    return data_source


def create_data_source(output_file):
    driver = ogr.GetDriverByName("ESRI Shapefile")
    if os.path.exists(output_file):
        os.remove(output_file)
    data_source = driver.CreateDataSource(output_file)
    return data_source


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


def parse_no_guess(input_pt, additional_pj=[]):
    output_guesses = Parse(input_pt, None, additional_pj)
    first_guess = output_guesses[0]
    output_pt, unmangler = first_guess[0], first_guess[1]
    distance = ""
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

#todo add https://pcjericks.github.io/py-gdalogr-cookbook/layers.html#create-a-new-shapefile-and-add-data
#todo documentation http://gdal.org/java/index.html?org/gdal/ogr/FieldDefn.html


def print_coordlist(coordlist):
    print("coordlist: ")
    for elem in coordlist:
        print(elem)
    print("end of coordlist")


class SingleCoord:
    def __init__(self, input_pt, attr="", center_pt=("", ""), output_pt=("", ""), distance="", unmangler="",
                 additional_pj=[], data=""):
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
        return "mangled: [{},{}], attr: {}, group: {}".format(self.input_pt[0], self.input_pt[1], self.attr, self.group)

    def set_fields(self, feature):
        feature.SetField("Mangled X", self.input_pt[0])
        feature.SetField("Mangled Y", self.input_pt[1])
        feature.SetField("Guess X", self.center_pt[0])
        feature.SetField("Guess Y", self.center_pt[1])
        feature.SetField("distance", self.distance)
        feature.SetField("Method", self.unmangler)
        feature.SetField("additional projection", self.additional_pj)
        feature.SetField("Other Data", self.data)






