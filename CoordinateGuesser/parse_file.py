from ogr import Geometry, wkbPoint
import osr, warnings

from .halfCorUnmanglers import *
from .unmanglerGenerator import *
from .normalize import normalize
from .parse import Parse, decToDmsCoor
from ..utilities import *
import csv


def getFeature(layerPath, myField, myValue):
    dataSource = ogr.Open(layerPath, 0)
    layer = dataSource.GetLayer()
    spatialRef = layer.GetSpatialRef()
    layerDefinition = layer.GetLayerDefn() #returns FeatureDefn object
    x,y = (None,None)
    lyrDefn = layer.GetLayerDefn()

    for feature in layer:
        if (feature.GetField(myField) == myValue or feature.GetField(myField) == float(myValue)):
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

def parseFile (colList,input_file,output_file, additional_pj=[]):
    """
    input_file : string
        path of a csv file
    output_file : string
        path of a csv file
http://www.gdal.org/ogr_arch.html
    """
    with open(input_file, newline='') as csv_input, open(output_file, 'w', newline='') as csv_output:
        reader = csv.DictReader(csv_input, delimiter=',', quotechar='|')
        writer = csv.writer(csv_output, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)

        writer.writerow(["mangled X", "mangled Y", "guess X", "guess Y", "layer", "field", "feature" \
                            , "unmangled X", "unmangled Y", "distance", "method"])
        mangledXCol, mangledYCol, guessXCol, guessYCol, layerCol, fieldCol, valueCol = colList
        colListNoNone = [x for x in colList if x is not None]
        input_pt = ("init out of loop", "1")

        usingGuess = True
        usingLayer = True
        guessInFile = True

        # no columns given for guess coord
        if not all((guessXCol, guessYCol)):
            # (guessXCol is None) or (guessYCol is None):
            usingGuess = False
        # no columns given for layer
        if not all((layerCol, fieldCol, valueCol)):
            # (layerCol is None) or (fieldCol is None) or (valueCol is None):
            usingLayer = False
        # neither layer nor guess coord
        if not any((usingGuess, usingLayer)):
            # usingGuess is False and usingLayer is False:
            guessInFile = False
        center_pt = ("init out of loop", "1")
        warnings.warn("out of i loop" + str(guessInFile))

        for i,row in enumerate(reader): #i is the index of the row
            try:
                print("in enumerate loop")

                center_pt = ("", "")
                output_pt = ("", "")
                unmangler = ""
                distance = ""
                layer = ""
                field = ""
                feature = ""

                input_pt = (row[mangledXCol], row[mangledYCol])
                print("input_pt: " + input_pt[0] + "," + input_pt[1])
                if not guessInFile: #is False:
                    output_pt, unmangler, distance = parseNoGuess(input_pt)

                elif usingGuess: #is True:
                    if all((row[guessXCol],row[guessYCol])):#row[guessXCol] and row[guessYCol]:
                        center_pt = (float(row[guessXCol]), float(row[guessYCol]))
                        output_pt, unmangler, distance = parseWithGuess(input_pt, center_pt)

                    elif usingLayer:# is True:
                        if all((row[layerCol],row[fieldCol],row[valueCol])):#row[layerCol] and row[fieldCol] and row[valueCol]:
                            layer = row[layerCol]
                            field = row[fieldCol]
                            feature = row[valueCol]
                            # warnings.warn("layer: "+str(layer) + " field: "+ field +" feature: "+ feature)
                            x, y = getFeature(layer, field, feature)
                            center_pt = (float(x), float(y))
                            output_pt, unmangler, distance = parseWithGuess(input_pt, center_pt)

                        else:
                            output_pt, unmangler, distance = parseNoGuess(input_pt)

                writer.writerow([*input_pt, *center_pt, layer, field, feature, *output_pt, distance, unmangler])

                print("{}: {}, {}, {}".format(i, *output_pt, unmangler, distance))
            except:
                writer.writerow([row, 'err'])

