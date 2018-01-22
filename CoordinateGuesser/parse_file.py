from ogr import Geometry, wkbPoint
import osr, warnings

from .halfCorUnmanglers import *
from .unmanglerGenerator import *
from .normalize import normalize
from .parse import Parse, decToDmsCoor

import csv

def parseFile (input_file, output_file,guessInFile=True, guessLatLong=None,guessLayer=None, additional_pj=[] ):
    """
    input_file : string
        path of a csv file
    output_file : string
        path of a csv file
    guessInFile : boolean
        indicates if there are guesses for the scrambled coordinate in file
    guessLatLong : tuple (preferably float)
        a guess coor (X,Y) common to all points. in the gui, it's chosen by capturing a point on map.
        if None than not used in parsing.
    guessLayer : tuple (preferably float)
        a guess coor (X,Y) common to all points. in the gui, it's chosen by choosing a layer's feature.
        if None than not used in parsing.

    """
    with open(input_file, newline='') as csv_input, open(output_file, 'w', newline='') as csv_output:
        reader = csv.reader(csv_input, delimiter=',', quotechar='|')
        writer = csv.writer(csv_output, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        # writer.writerow(['Spam'] * 5 + ['Baked Beans'])
        # writer.writerow(['Spam', 'Lovely Spam', 'Wonderful Spam'])
        #the header for the output file
        if guessLatLong != None:
            writer.writerow(
                ["mangled X", "mangled Y", "guess X", "guess Y", "unmangled X", "unmangled Y", "distance", "method",\
                 "","by a given long-lat"])
        elif guessLayer != None:
            writer.writerow(
                ["mangled X", "mangled Y", "guess X", "guess Y", "unmangled X", "unmangled Y", "distance", "method",\
                 "", "by the center of a feature"])
        else:
            writer.writerow(["mangled X","mangled Y", "guess X", "guess Y","unmangled X","unmangled Y","distance","method"])
        for i,row in enumerate(reader): #i is the index of the row
            try:
            # if len(row)>=4:
                usingGuess=True
                center_pt = None
                print('{}: {}'.format(i, row))#prints the row's index and then the whole row
                input_pt = tuple(row[0:2])
                print("input_pt: " +input_pt[0] +"," + input_pt[1])

            #the guess is determined by the booleans guessInFile, guessLatLong, guessLayer
                if guessInFile == True:
                    #warnings.warn("guessInFile == True")
                    #if ((row[2] != None) and (row[3] != None)):
                    if (len(row)>3):
                        center_pt = (float(row[2]),float(row[3]))
                    else:
                        center_pt = (None,None)
                        center_pt = None
                        usingGuess = False #the only instance where not using a guess coordinate

                elif guessLatLong != None:
                    center_pt = (float(guessLatLong[0]),float(guessLatLong[1]))
                elif guessLayer != None:
                    center_pt = (float(guessLayer[0]),float(guessLayer[1]))
                output_guesses = Parse(input_pt, center_pt, additional_pj)
                first_guess = output_guesses[0]
                #if there was a use of a guess in the use of parse
                if usingGuess==True:
                    output_pt, unmangler, distance = first_guess[0], first_guess[1], first_guess[2]
                    writer.writerow([*input_pt, *center_pt, *output_pt, distance, unmangler])

                # if there wasn't a use of a guess in the use of parse
                elif usingGuess==False:
                    output_pt, unmangler = first_guess[0], first_guess[1]
                    distance = "no guess given"
                    writer.writerow([*input_pt, "none", "none", *output_pt, distance, unmangler])

                print("{}: {}, {}, {}".format(i, decToDmsCoor(*output_pt), unmangler, distance))
            except:
                writer.writerow([row, 'err'])
