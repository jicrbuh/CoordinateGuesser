from ogr import Geometry, wkbPoint
import osr, warnings

from .halfCorUnmanglers import *
from .unmanglerGenerator import *
from .normalize import normalize
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
        print(myValue + " " + feature.GetField(myField))
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

def parseWithLayer(input_pt, layer, field,value,additional_pj=[]):
    center_pt = getFeature(layer,field,value)
    output_guesses = Parse(input_pt, center_pt, additional_pj)
    first_guess = output_guesses[0]
    output_pt, unmangler, distance = first_guess[0], first_guess[1], first_guess[2]
    return (output_pt, unmangler, distance)



def parseFileNoCol(input_file,output_file,guessX,guessY,layer=None, field = None, additional_pj=[]):
    myencoding = get_encoding_by_bom(input_file)
    with open(input_file, newline='', encoding=myencoding) as csv_input, open(output_file, 'w', newline='') as csv_output:
        reader = csv.reader(csv_input, delimiter=',', quotechar='"')
        writer = csv.writer(csv_output, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)

        writer.writerow(["mangled X", "mangled Y", "guess X", "guess Y", "unmangled X",
                         "unmangled Y", "distance [km]", "method","additional_pj","other data from file"])
        center_pt = ("", "")
        usingGuess = guessY and guessX
        if usingGuess:
            center_pt = (guessX,guessY)
        #if there's layer and field then we use the third column
        usingField = layer and field

        for i,row in enumerate(reader): #i is the index of the row

            try:

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
                else:
                    writer.writerow([*input_pt, *center_pt, *output_pt, distance/1000, unmangler,additional_pj, *row[2:]])

                print("{}: {}, {}, {}".format(i, *output_pt, unmangler, distance/1000))
            except:
                writer.writerow(["error","","","","","","","","",*row])

