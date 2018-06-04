# -*- coding: utf-8 -*-
"""
 CoordGuesserDialog
                                 A QGIS plugin
/***************************************************************************
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
from qgis.core import QgsProject, QgsPointXY, QgsMapLayer
from qgis.gui import QgsMessageBar
from PyQt5.QtCore import *

from .CoordinateGuesser import parse
from .CoordinateGuesser import Parse, parse_file
#from qgis.utils import iface
import re, warnings, csv

def staticSetCoor(destinationLineEdit,x,y):
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
        self.canvas = iface.mapCanvas()
        self.iface = iface
        self.getLayers(self.selectLayerComboBox)
        #todo use staticSetCoor for self.coorTool
        self.VMarker = QgsVertexMarker(self.canvas)
        self.VMarker.hide()
        self.coorTool = getCoordinateTool(self,self.canvas,self.setCoor, QgsProject.instance(),self.VMarker)
        #unmangledMarker = QgsVertexMarker(self.canvas)
        self.unmangledMarker = QgsVertexMarker(self.canvas)
        self.unmangledMarker.setColor(Qt.blue)
        self.unmangledMarker.hide()
        self.unmangledMarker.setPenWidth(3)
        self.VMarker.setPenWidth(3)

        ######################
        ######connects#######
        ######################
        self.pushButton_Capture.clicked.connect(self.captureButtonClick)
        self.selectLayerComboBox.currentIndexChanged.connect(self.getFieldList)
        self.selectFieldComboBox.currentIndexChanged.connect(self.onFieldSelected)
        self.pushButton_Go.pressed.connect(self.guessCoor)  # if Go! button is pushed, guess the coor using parse
        self.pushButton_browse.pressed.connect(lambda: self.getFilePath(0))
        self.checkBox_attr.stateChanged.connect(self.onChangedAttrCheckBox)
        self.selectFeatureComboBox.activated.connect(self.onFeatureSelected)

    def onChangedAttrCheckBox(self,int):
        self.fromLayerRadioButton.setChecked(True)
        if int == 2:
            self.selectFeatureComboBox.setEnabled(False)
        elif int ==0:
            self.selectFeatureComboBox.setEnabled(True)

    def captureButtonClick(self):
        self.fromMapRadioButton.setChecked(True)
        self.canvas.setMapTool(self.coorTool)
        self.coorTool.clean()

    def setCoor(self,x,y):
        self.lineEdit_latLong.setText(f"{x:10.10f}, {y:10.10f}")

    def getLayers(self, destinationComboBox):
        layersDict = QgsProject.instance().mapLayers()
        allLayers = list(layersDict.values())
        destinationComboBox.clear()
        vectorList = []
        for layer in allLayers:
            if layer.type() == QgsMapLayer.VectorLayer:
                # allLayers.remove(layer)
                vectorList.append(layer)

        try:
            vectorList = sorted(vectorList, key=lambda layer: layer.name().lower(), reverse=True)
        except AttributeError:
            vectorList = sorted(vectorList, key=lambda layer: layer.name(), reverse=True)

        for layer in vectorList:
            # comboBox.insertItem(float('inf'), layer.name(), layer)
            destinationComboBox.insertItem(float('inf'), layer.name(), layer)
        destinationComboBox.setCurrentIndex(0)
        if len(vectorList) > 0:
            print(str(len(vectorList)))
            self.getFieldList(0)

    def onLayerSelected(self, ind):
        """gets all the features of a selected layer into the combobox"""
        selectedLayer = self.selectLayerComboBox.currentData()
        features = self.getFeatures(selectedLayer)
        self.selectFeatureComboBox.clear()
        for (name, value) in features:
            self.selectFeatureComboBox.insertItem(float('inf'), name, value)
        #self.getFieldList(0)

    def getFieldList(self, ind):
        self.fromLayerRadioButton.setChecked(True)
        # todo https://gis.stackexchange.com/questions/212618/check-particular-feature-exists-using-pyqgis
        selectedLayer = self.selectLayerComboBox.currentData()
        fieldList = []

        fields = selectedLayer.fields()


        try:
            fields = sorted(fields, key=lambda field: field.name().lower(), reverse=True)
        except AttributeError:
            fields = sorted(fields, key=lambda field: field.name(), reverse=True)

        self.selectFieldComboBox.clear()

        for field in fields:
            warnings.warn(str(field.name()))
            self.selectFieldComboBox.insertItem(float('inf'), field.name(), field)
        self.selectFieldComboBox.setCurrentIndex(0)
        self.onFieldSelected(0)

    def onFieldSelected(self,ind):
        """after the user selects a field from the combobox, the feature combobox updates with the field values"""
        self.fromLayerRadioButton.setChecked(True)
        self.selectFeatureComboBox.clear()
        selectedLayer = self.selectLayerComboBox.currentData()
        selectedField = self.selectFieldComboBox.currentData()
        selectedFieldName = self.selectFieldComboBox.currentText()
        layerCRS = selectedLayer.crs()
        #index = selectedLayer.fieldNameIndex(selectedField)
        features = selectedLayer.getFeatures()

        if selectedFieldName:
            try:
                features = sorted(features, key=lambda feature: feature.attribute(selectedFieldName),
                                  reverse=True)
            except AttributeError:
                features=sorted(features, key=lambda feature: feature.attribute(selectedFieldName).lower(), reverse=True)

            for feature in features:
                myattr = feature.attribute(selectedFieldName)
                ctrPoint = feature.geometry().centroid().asPoint()
                #print(str(ctrPoint))
                (x, y) = coorTransform(ctrPoint, layerCRS, QgsProject.instance())
                self.selectFeatureComboBox.insertItem(float('inf'), str(myattr), (x,y))
        self.selectFeatureComboBox.setCurrentIndex(0)
        self.onFeatureSelected(0)

    def getFeatures(self, mylayer):
        """gets all the features (and their center coor) for the selected layer"""
        self.fromLayerRadioButton.setChecked(True)

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
        self.fromLayerRadioButton.setChecked(True)

        if self.selectFeatureComboBox.currentData():
            centerPoint = self.selectFeatureComboBox.currentData()
            (x1,y1) = self.selectFeatureComboBox.currentData()
            selectedLayer = self.selectLayerComboBox.currentData()
            layerCRS = selectedLayer.crs()
            staticSetCoor(self.lineEdit_centroid, x1, y1)
        #if centerPoint is None:
         #   (x, y) = coorTransform(selectedLayer.extent().center(), layerCRS, QgsProject.instance())
       # else:
       #     (x,y) = coorTransform(centerPoint, layerCRS, QgsProject.instance())
        #this line changes the coor in the lineEdit_latLong


    def guessCoor(self):
        # coortext is the scrambled coor, xydelim is the user's delimiter
        coorText = self.scrambled.text()
        additionProj = self.getAdditionalProj()
        layer = None
        field = None


        #single mode
        if self.radioButton_single.isChecked():
            # (x, y) = re.split(self.xydelim.text(), coorText, 1)
            # if the delimiter isn't found in the user's scrambled text an error message
            try:
                (x, y) = re.split(self.xydelim.text(), coorText, 1)
                (x,y) = (x.strip(),y.strip())
            except ValueError:
                self.changeMessage("ERROR: XY delimiter not found in scrambled coor")
                return

            try:
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
                    (guessX,guessY) = self.lineEdit_centroid.text().split(', ') #guess is the centroid of selected feature
                    output_guesses = Parse((x, y), (float(guessX),float(guessY)), additionProj)
                    self.showOutputs(output_guesses)
            except:
                self.changeMessage("ERROR: Could not parse coordinate")
                self.clearOutpus()
        #batch mode
        else:
            if self.checkBox_attr.isChecked():
                print("attr is checked")

                layer = self.selectLayerComboBox.currentData()
                path = layer.dataProvider().dataSourceUri()
                path = path[:path.rfind('|')]
                layer = path

                field = self.selectFieldComboBox.currentText()
                print(path + " "+field)

            inputPath,outpuPath = self.getInOutPath()
            guessX, guessY = (None,None)
            if self.fromMapRadioButton.isChecked() == True:
                (guessX, guessY) = self.lineEdit_latLong.text().split(', ')  # guess is the point the user clicked
                (guessX, guessY) = (float(guessX), float(guessY))
            if self.fromLayerRadioButton.isChecked() == True and self.checkBox_attr.isChecked() == False:
                (guessX, guessY) = self.lineEdit_centroid.text().split(', ')  # guess is the centroid of selected feature
            try:
                parse_file.parseFileNoCol(inputPath,outpuPath,guessX,guessY,layer,field,additionProj)
                self.clearOutpus()
                self.changeMessage("File created successfully at: " + outpuPath)
            except PermissionError:
                self.clearOutpus()
                self.changeMessage("PermissionError: please close input and output files")

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
        first_guess = output_guesses[0][0]
        # isguess - did user choose a guess (if chose "no given guess"-> isguess=False)
        if isguess == True:
            output_pt, unmangler, distance = first_guess[0],first_guess[1],first_guess[2]
            self.out_xy.setText(f"{output_pt[0]:10.10f}, {output_pt[1]:10.10f}")
            distanceInKm = distance/1000

            self.distance.setText(f"{distance:10.5f}" + " deg")
            #self.distance.setText(f"{distanceInKm:10.5f}" + " km")
            self.method_used.setText(unmangler)

        else:
            output_pt, unmangler = first_guess[0],first_guess[1]
            self.out_xy.setText(f"{output_pt[0]:10.10f}, {output_pt[1]:10.10f}")
            self.distance.setText(f"No guess given")
            self.method_used.setText(unmangler)
        unmangledPt = QgsPointXY(float(output_pt[0]), float(output_pt[1]))
        self.unmangledMarker.setCenter(unmangledPt)
        self.unmangledMarker.show()

    def clearOutpus(self):
        self.out_xy.setText("")
        self.distance.setText("")
        self.method_used.setText("")

    def visChange(self, visible):
        self.tell(visible)

    def closeEvent(self, event):
        """on closing the main window, deleting the markers"""
        self.canvas.scene().removeItem(self.VMarker)
        self.canvas.scene().removeItem(self.unmangledMarker)

    def getInOutPath(self):
        inputPath = self.lineEdit_filePath.text()
        (dirPath, fileName) = os.path.split(os.path.abspath(inputPath))

        newFileName = os.path.splitext(fileName)[0] +"_output" +'.csv'
        outputPath = os.path.join(dirPath, newFileName)
        return (inputPath,outputPath)


    def getFilePath(self, isShpFile):
        """opens the file browser and gets the csv file path from the user"""
        self.radioButton_batch.setChecked(True)
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


