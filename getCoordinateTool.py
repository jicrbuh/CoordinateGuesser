from qgis.gui import QgsMapTool, QgsVertexMarker
from PyQt5 import uic, QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal
from .utilities import *
from qgis.core import QgsProject, QgsCoordinateReferenceSystem, QgsCoordinateTransform
class getCoordinateTool (QgsMapTool):
    def __init__(self,owner, canvas,onclick, projectInstance,VMarker):
        """constructor"""
        super().__init__(canvas)
        self.owner = owner
        self.canvas = canvas
        self.onClick = onclick
        self.project_instance = projectInstance
        self.VMarker = VMarker

    def canvasPressEvent(self, e):
        #self.clean()
        super().canvasPressEvent(e)
        pos=self.toMapCoordinates(e.pos())
        crsSrc = QgsProject.instance().crs()
        (x,y) = coorTransform(pos, crsSrc,self.project_instance)
        self.onClick(x,y)
        self.centeringMarker(pos)
        #deactivate the select tool
        self.canvas.unsetMapTool(self)

    def centeringMarker(self,e):
        #m = QgsVertexMarker(self.canvas)
        self.VMarker.setCenter(e)
        self.VMarker.show()

#todo https://qgis.org/api/classQgsVertexMarker.html create this object and connect it to a clickevent
#todo https://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/canvas.html#writing-custom-map-tools
#todo https://github.com/mpetroff/qgsazimuth

