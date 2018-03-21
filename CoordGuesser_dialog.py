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
from qgis.gui import QgsVertexMarker

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
        ###############
        #not a 'connect'
        ################
        self.canvas = iface.mapCanvas()
        self.iface = iface
        getLayers(self.selectLayerComboBox)
        #todo use staticSetCoor for self.coorTool
        m = QgsVertexMarker(self.canvas)
        self.VMarker = m
        self.VMarker.hide()
        self.coorTool = getCoordinateTool(self,self.canvas,self.setCoor, QgsProject.instance(),self.VMarker)

        ######################
        ######connects#######
        ######################
        self.pushButton_Capture.clicked.connect(self.captureButtonClick)
        #self.selectLayerComboBox.currentIndexChanged.connect(self.onLayerSelected)
        self.selectLayerComboBox.currentIndexChanged.connect(self.getFieldList)
        #self.selectFeatureComboBox.currentIndexChanged.connect(self.onFeatureSelected)  #old
        self.selectFieldComboBox.currentIndexChanged.connect(self.onFieldSelected)
        self.pushButton_Go.pressed.connect(self.guessCoor)  # if Go! button is pushed, guess the coor using parse
        #self.pushButton_Batch.pressed.connect(self.handleBatchPress)
        self.pushButton_browse.pressed.connect(lambda: self.getFilePath(0))



    def captureButtonClick(self):
        self.canvas.setMapTool(self.coorTool)
        self.coorTool.clean()

    def setCoor(self,x,y):
        #self.lineEdit_latLong.setText(f"{x}, {y}")
        #changed the number format to include less digits after the decimal point
        self.lineEdit_latLong.setText(f"{x:10.10f}, {y:10.10f}")

    #def trysetCoortrysetCoor(self, lineEdit):
        #return staticSetCoor(lineEdit,x,y)

    #"""gets all the layers in the map into the combobox"""
    #def getLayers(self):
   #     layersDict = QgsProject.instance().mapLayers()
    #    allLayers = list(layersDict.values())
    #    self.selectLayerComboBox.clear()
    #    for layer in allLayers:
    #        #comboBox.insertItem(float('inf'), layer.name(), layer)
     #       self.selectLayerComboBox.insertItem(float('inf'), layer.name(), layer)

    """gets all the features of a selected layer into the combobox"""
    def onLayerSelected(self, ind):
        #warnings.warn("onLayerSelected")
        selectedLayer = self.selectLayerComboBox.currentData()
        features = self.getFeatures(selectedLayer)
        self.selectFeatureComboBox.clear()
        for (name, value) in features:
            self.selectFeatureComboBox.insertItem(float('inf'), name, value)
        #self.getFieldList(0)

    def getFieldList(self, ind):
        # todo https://gis.stackexchange.com/questions/212618/check-particular-feature-exists-using-pyqgis
        #warnings.warn("GetFieldsList")
        selectedLayer = self.selectLayerComboBox.currentData()
        fieldList = []
        fields = selectedLayer.fields()
        self.selectFieldComboBox.clear()
        for field in fields:
            warnings.warn(str(field.name()))
            self.selectFieldComboBox.insertItem(float('inf'), field.name(), field)

    """after the user selects a field from the combobox, the feature combobox updates with the field values"""
    def onFieldSelected(self,ind):
        self.selectFeatureComboBox.clear()
        selectedLayer = self.selectLayerComboBox.currentData()
        selectedField = self.selectFieldComboBox.currentData()
        selectedFieldName = self.selectFieldComboBox.currentText()
        #index = selectedLayer.fieldNameIndex(selectedField)
        features = selectedLayer.getFeatures()
        if selectedFieldName:
            for feature in features:
                myattr = feature.attribute(selectedFieldName)
                ctrPoint = feature.geometry().centroid().asPoint()
                self.selectFeatureComboBox.insertItem(float('inf'), str(myattr), ctrPoint)

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
        additionProj = self.getAdditionalProj()
        #print("additionProj: " + str(additionProj))

        #single mode
        if self.radioButton_single.isChecked():
            # (x, y) = re.split(self.xydelim.text(), coorText, 1)
            # if the delimiter isn't found in the user's scrambled text an error message
            try:
                (x, y) = re.split(self.xydelim.text(), coorText, 1)
            except ValueError:
                self.changeMessage("ERROR: XY delimiter not found in scrambled coor")
                return

            if self.noGivenRadioButton.isChecked() == True:
                output_guesses = Parse((x, y),None,additionProj) #uncomment if you don't want parse to split the str coortext
                #output_guesses = Parse(coorText, delimiter=self.xydelim.text())
                self.showOutputs(output_guesses,isguess=False)

            if self.fromMapRadioButton.isChecked() == True:
                (guessX,guessY) = self.lineEdit_latLong.text().split(', ') #guess is the point the user clicked
                (guessX, guessY) = (float(guessX),float(guessY))
                output_guesses = Parse((x, y), (guessX,guessY),additionProj)
                self.showOutputs(output_guesses)

            if self.fromLayerRadioButton.isChecked() == True:
                (guessX,guessY) = self.selectFeatureComboBox.currentData() #guess is the centroid of selected feature
                output_guesses = Parse((x, y), (float(guessX),float(guessY)), additionProj)
                self.showOutputs(output_guesses)
        #batch mode
        else:
            inputPath,outpuPath = self.getInOutPath()
            guessX, guessY = (None,None)
            if self.fromMapRadioButton.isChecked() == True:
                (guessX, guessY) = self.lineEdit_latLong.text().split(', ')  # guess is the point the user clicked
                (guessX, guessY) = (float(guessX), float(guessY))
            if self.fromLayerRadioButton.isChecked() == True:
                (guessX, guessY) = self.selectFeatureComboBox.currentData()  # guess is the centroid of selected feature
            parse_file.parseFileNoCol(inputPath,outpuPath,guessX,guessY,additionProj)
            self.changeMessage("File created successfully at: " + outpuPath)

    def getAdditionalProj(self):
        addProjText = self.lineEdit_addProj.text()
        if addProjText:
            if len(addProjText) in range(1,3):
                try:
                    myzone = int(addProjText)
                    return [myzone]
                except ValueError:
                    return []
            elif isinstance(addProjText, str):
                destproj = osr.SpatialReference()
                errorInt = destproj.ImportFromProj4(addProjText)
                if errorInt == 5:
                    self.changeMessage("ERROR: Additional projection isn't a valid PROJ.4 string")
                    return []

                return [addProjText]
        return []

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

    """on closing the main window, the red marker is deleted"""
    def closeEvent(self, event):
        self.canvas.scene().removeItem(self.VMarker)

    def getInOutPath(self):
        inputPath = self.lineEdit_filePath.text()
        (dirPath, fileName) = os.path.split(os.path.abspath(inputPath))
        newFileName = "batched_" + fileName
        outputPath = os.path.join(dirPath, newFileName)
        return (inputPath,outputPath)

    """opens the file browser and gets the csv file path from the user"""

    def getFilePath(self, isShpFile):
        if isShpFile == 0:
            filename1 = QFileDialog.getOpenFileName(self, str("Open File"), "", str("CSV Files (*.csv)"))
            ##filename1 is a tuple, filename[0] is the path, filename[1] is the file type
            if filename1[0] != None:
                self.lineEdit_filePath.setText(filename1[0])

        else:
            filename1 = QFileDialog.getOpenFileName(self, str("Open File"), "", str("SHP Files (*.shp)"))
            ##filename1 is a tuple, filename[0] is the path, filename[1] is the file type
            if filename1[0] != None:
                self.lineEdit_filePath.setText(filename1[0])


    def changeMessage(self, mytext):
        self.label_message.setText(mytext)
        QTimer.singleShot(8000, self.resetMessage)

    def resetMessage(self):
        self.label_message.setText("")


