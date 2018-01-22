from qgis.gui import QgsMapTool
from PyQt5 import uic, QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal
from .utilities import *
from qgis.core import QgsProject, QgsCoordinateReferenceSystem, QgsCoordinateTransform
class getCoordinateTool (QgsMapTool):
    def __init__(self,owner, canvas,onclick):
        """constructor"""
        super().__init__(canvas)
        self.owner = owner
        self.canvas = canvas
        self.onClick = onclick
    def deactivate(self):
        super().deactivate()

    def canvasPressEvent(self, e):
        super().canvasPressEvent(e)
        pos=self.toMapCoordinates(e.pos())
        crsSrc = QgsProject.instance().crs()
        (x,y) = coorTransform(pos, crsSrc,projectInstance)
        self.onClick(x,y)
        #deactivate the select tool
        self.deactivate()
