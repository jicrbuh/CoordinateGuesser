# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CoordGuesserDialog
                                 A QGIS plugin
 Parse, unscramble, guess coordinates
                             -------------------
        begin                : 2017-10-19
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Idan Miara
        email                : idan@miara.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QFileDialog
from osgeo import ogr, osr
from .getCoordinateTool import getCoordinateTool

from .utilities import *
from qgis.core import QgsProject
from qgis.core import QgsMapLayer
from qgis.gui import QgsMessageBar
from PyQt5.QtCore import *

from .CoordinateGuesser import parse
from .CoordinateGuesser import Parse, parse_file
#from qgis.utils import iface
import re, warnings, csv

def getLayers(destinationComboBox):
    layersDict = QgsProject.instance().mapLayers()
    allLayers = list(layersDict.values())
    destinationComboBox.clear()
    vectorList = []
    for layer in allLayers:
        if layer.type() == QgsMapLayer.VectorLayer:
            #allLayers.remove(layer)
            vectorList.append(layer)
    for layer in vectorList:
        #comboBox.insertItem(float('inf'), layer.name(), layer)
        destinationComboBox.insertItem(float('inf'), layer.name(), layer)

def staticSetCoor(destinationLineEdit,x,y):
    #self.lineEdit_latLong.setText(f"{x}, {y}")
    #changed the number format to include less digits after the decimal point
    destinationLineEdit.setText(f"{x:10.10f}, {y:10.10f}")

#new declaration of ui
MainWindowUI, MainWindowBase = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'CoordGuesser_dialog_base.ui'))

BrowserUI, BrowserBase = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'CoordGuesser_fileBrowser_240118.ui'))

#old declaration of ui
#FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'CoordGuesser_dialog_base.ui'))

#class CoordGuesserDialog(QtWidgets.QDialog, FORM_CLASS): #old
class CoordGuesserDialog(MainWindowBase, MainWindowUI):# new
    def tell(self, mess):
        QtWidgets.QMessageBox.information(self, "DEBUG: ", str(mess))

    def __init__(self, parent, iface):
        """Constructor."""
        super().__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        ######################
        ######connects#######
        ######################
        self.pushButton_Capture.clicked.connect(self.captureButtonClick)
        self.selectLayerComboBox.currentIndexChanged.connect(self.onLayerSelected)
        self.selectFeatureComboBox.currentIndexChanged.connect(self.onFeatureSelected) # if user chose a feature, show its coordinate
        self.pushButton_Go.pressed.connect(self.guessCoor) # if Go! button is pushed, guess the coor using parse
        self.pushButton_Batch.pressed.connect(self.handleBatchPress)
        ###############
        #not a 'connect'
        ################
        self.canvas = iface.mapCanvas()
        #todo use staticSetCoor for self.coorTool
        self.coorTool = getCoordinateTool(self,self.canvas,self.setCoor, QgsProject.instance())
        getLayers(self.selectLayerComboBox)
        self.iface = iface

    def captureButtonClick(self):
        #todo make the button deactivate itself after one point choice
        self.canvas.setMapTool(self.coorTool)

    def setCoor(self,x,y):
        #self.lineEdit_latLong.setText(f"{x}, {y}")
        #changed the number format to include less digits after the decimal point
        self.lineEdit_latLong.setText(f"{x:10.10f}, {y:10.10f}")

    def trysetCoor(self, lineEdit):
        return staticSetCoor(lineEdit,x,y)

    #"""gets all the layers in the map into the combobox"""
    #def getLayers(self):
   #     layersDict = QgsProject.instance().mapLayers()
    #    allLayers = list(layersDict.values())
    #    self.selectLayerComboBox.clear()
    #    for layer in allLayers:
    #        #comboBox.insertItem(float('inf'), layer.name(), layer)
     #       self.selectLayerComboBox.insertItem(float('inf'), layer.name(), layer)

    #gets all the features of a selected layer into the combobox
    def onLayerSelected(self, ind):
        selectedLayer = self.selectLayerComboBox.currentData()
        features = self.getFeatures(selectedLayer)
        self.selectFeatureComboBox.clear()
        for (name, value) in features:
            self.selectFeatureComboBox.insertItem(float('inf'), name, value)

    """gets all the features (and their center coor) for the selected layer"""
    def getFeatures(self, mylayer):
        def describe(feature):
            fieldCount = len(feature.fields())
            return ", ".join(str(feature[i]) for i in range(fieldCount))
        #check if layer is vector layer
        if mylayer.type() == QgsMapLayer.VectorLayer:
            features = mylayer.getFeatures()
            #self.tell(dir(next(features)))
            #return
            return [(describe(f),f.geometry().centroid().asPoint()) for f in features]
        elif mylayer.type() == QgsMapLayer.RasterLayer:
            layerCenter = mylayer.extent().center()
            return [('center', layerCenter)]
        return []

    def onFeatureSelected(self, int):
        centerPoint = self.selectFeatureComboBox.currentData()
        selectedLayer = self.selectLayerComboBox.currentData()
        layerCRS = selectedLayer.crs()
        if centerPoint is None:
            (x, y) = coorTransform(selectedLayer.extent().center(), layerCRS, QgsProject.instance())
        else:
            (x,y) = coorTransform(centerPoint, layerCRS, QgsProject.instance())
        #this line changes the coor in the lineEdit_latLong
        self.setCoor(x,y)

    def guessCoor(self):
        # coortext is the scrambled coor, xydelim is the user's delimiter
        coorText = self.scrambled.text()
        #(x, y) = re.split(self.xydelim.text(), coorText, 1)
        #if the delimiter isn't found in the user's scrambled text an error message
        try:
            (x,y) = re.split(self.xydelim.text(),coorText,1)
        except ValueError:
            self.iface.messageBar().pushMessage("Error", "XY delimiter not found in scrambled coor", level=QgsMessageBar.WARNING)
            return

        #radioButton cases - map click, layer\feature, or no guess
        if self.noGivenRadioButton.isChecked() == True:
            output_guesses = Parse((x, y)) #uncomment if you don't want parse to split the str coortext
            #output_guesses = Parse(coorText, delimiter=self.xydelim.text())
            self.showOutputs(output_guesses,isguess=False)

        if self.fromMapRadioButton.isChecked() == True:
            (guessX,guessY) = self.lineEdit_latLong.text().split(', ') #guess is the point the user clicked
            (guessX, guessY) = (float(guessX),float(guessY))
            output_guesses = Parse((x, y), (guessX,guessY))
            self.showOutputs(output_guesses)

        if self.fromLayerRadioButton.isChecked() == True:
            (guessX,guessY) = self.selectFeatureComboBox.currentData() #guess is the centroid of selected feature
            output_guesses = Parse((x, y), (float(guessX),float(guessY)))
            self.showOutputs(output_guesses)

    def showOutputs(self, *output_guesses, isguess=True):
        #warnings.warn("output_guesses type: " + str(type(output_guesses))) # 'tuple'
        #warnings.warn("output_guesses[0] type: " + str(type(output_guesses[0])))  # 'list
        #warnings.warn("output_guesses[0][0] type: " + str(type(output_guesses[0][0]))) #'tuple'
        first_guess = output_guesses[0][0]
        # isguess - did user choose a guess (if chose "no given guess"-> isguess=False)
        if isguess == True:
            #warnings.warn(str(output_guesses[1])) there's no output_guesses[1]!
            output_pt, unmangler, distance = first_guess[0],first_guess[1],first_guess[2]
            self.out_xy.setText(f"{output_pt[0]:10.10f}, {output_pt[1]:10.10f}")
            self.distance.setText(f"{distance:10.10f}")
            self.method_used.setText(unmangler)
        else:
            output_pt, unmangler = first_guess[0],first_guess[1]
            self.out_xy.setText(f"{output_pt[0]:10.10f}, {output_pt[1]:10.10f}")
            self.distance.setText(f"No guess given")
            self.method_used.setText(unmangler)

    """shows the browsing window after clicking on batch Mode"""
    def handleBatchPress(self):
        # keep a reference to the Batch Browse ui
        self.browsing = BrowserDialog(self,self.iface)
        self.browsing.show()

    def visChange(self, visible):
        self.tell(visible)

"""class of the Batch Mode dialog box"""
class BrowserDialog(BrowserBase, BrowserUI):
#class BrowserDialog( CoordGuesserDialog):
    def __init__(self, parent,iface):
        #BrowserBase.__init__(self, parent)
        super().__init__(parent)
        self.setupUi(self)
        #################
        #not a 'connect'#
        ################
        self.iface=iface
        self.canvas = iface.mapCanvas()
        ###########
        # connects#
        ###########
        self.pushButton_Browse.pressed.connect(lambda: self.getFilePath(0))
        self.lineEdit_Path.textChanged.connect(self.getCsvHeaders)
        self.lineEdit_Path.textChanged.connect(self.guessHeaders)
        self.pushButton_Batch.pressed.connect(self.onBatchPressed)
        #self.mangledYCheckBox.toggled.connect(lambda: self.onCheckBoxSelected(self.mangledYComboBox, self.mangledXComboBox))
        #self.guessYCheckBox.pressed.connect(self.isGuessChecked)
        #self.guessYCheckBox.pressed.connect(lambda: self.onCheckBoxSelected(self.guessYComboBox, self.guessXComboBox))

    """when 'batch!' is pressed this function creates a file with the unscrambled coordinates"""
    def onBatchPressed(self):

        mangledXIdx = self.mangledXComboBox.currentIndex()
        mangledYIdx = self.mangledYComboBox.currentIndex()
        #guessXIdx = self.guessXComboBox.currentIndex()
        #guessYIdx = self.guessYComboBox.currentIndex()
        #layerIdx = self.layerComboBox.currentIndex()
        #fieldIdx = self.fieldComboBox.currentIndex()
        #valueIdx = self.fieldValueComboBox.currentIndex()
        # if mangledX\Y isn't chosen (idx 0) -> error
        if (mangledXIdx == 0 or mangledYIdx == 0):
            self.iface.messageBar().pushMessage("Error", "Mangled X\Y are required!",
                                            level=QgsMessageBar.WARNING)
            return
        colList = []
        comboList = self.getComboBoxList()
        for box in comboList:
            if box.currentIndex() == 0:
                colList.append(None)
            else:
                colList.append(box.currentData())
        inputPath = self.lineEdit_Path.text()
        (dirPath, fileName) = os.path.split(os.path.abspath(inputPath))
        newFileName = "batched_" + fileName
        outputPath = os.path.join(dirPath, newFileName)
        parse_file.parseFile(colList,inputPath,outputPath)

    """updates all comboBoxes to csv header"""
    def getCsvHeaders(self):
        inputPath = self.lineEdit_Path.text()
        #fills all comboBoxes with the same list of headers
        headerList = self.getHeaderList()
        #warnings.warn("got into getCsvHeaders" + str(headerList))
        comboBoxList = self.getComboBoxList()
        if headerList is not None and comboBoxList is not None:
            for box in comboBoxList:
                self.insertListToBox(box,headerList)
        #self.guessHeaders()

    def getComboBoxList(self):
        return [self.mangledXComboBox,self.mangledYComboBox, self.guessXComboBox, self.guessYComboBox,
                self.layerComboBox,self.fieldComboBox,self.fieldValueComboBox]

    def getComboBoxNamesList(self):
        return ["mangled X","mangled Y", "guess X", "guess Y","Layer","field","value"]

    def insertListToBox(self, destinationComboBox, tupleOfLists):
        destinationComboBox.clear()
        rowNumList = tupleOfLists[0]
        valueList = tupleOfLists[1]
        for i in range(0,len(valueList)):
            destinationComboBox.addItem(valueList[i],rowNumList[i])

    #todo fix it. the function is called but doesn't work
    """ automatically pairs the comboBox and the correct row, if exists """
    def guessHeaders(self):
        comboBoxNameList = self.getComboBoxNamesList()
        comboBoxList = self.getComboBoxList()
        for i in range (0,len(comboBoxList)):
            box = comboBoxList[i]
            boxName = comboBoxNameList[i]
            index = box.findText(boxName, QtCore.Qt.MatchFixedString)
            if index >= 0:
                box.setCurrentIndex(index)

    """ gets header list from chosen .csv file into the dialog window"""
    def getHeaderList(self):
        inputPath = self.lineEdit_Path.text()
        with open(inputPath) as csvfile:
            csv_reader = csv.reader(csvfile)
            #reading csv file and getting the first line (header)
            csv_headings = next(csv_reader)
            rowNumList=[None]
            valueList=[""]
            headingTuple = ()
            for i in range(0,len(csv_headings)):
                rowNumList.append(i)
                valueList.append(csv_headings[i])
            return (rowNumList,valueList)

    """opens the file browser and gets the csv file path from the user"""
    def getFilePath(self,isShpFile):
        if isShpFile==0:
            filename1 = QFileDialog.getOpenFileName(self, str("Open File"), "/", str("CSV Files (*.csv)"))
            ##filename1 is a tuple, filename[0] is the path, filename[1] is the file type
            if filename1[0] != None:
                self.lineEdit_Path.setText(filename1[0])

        else:
            filename1 = QFileDialog.getOpenFileName(self, str("Open File"), "/", str("SHP Files (*.shp)"))
            ##filename1 is a tuple, filename[0] is the path, filename[1] is the file type
            if filename1[0] != None:
                self.lineEdit_shpPath.setText(filename1[0])

    def isGuessChecked(self, mybool):
        if mybool is True:
            self.onCheckBoxSelected(self.guessYComboBox, self.guessXComboBox)

    def isMangledChecked(self, mybool):
        if mybool is True:
            self.onCheckBoxSelected(self.mangledYComboBox, self.mangledXComboBox)

    def onCheckBoxSelected(self, currentComboBox, previousComboBox):
        idx = previousComboBox.currentIndex()
        currentComboBox.setCurrentIndex(idx+1)