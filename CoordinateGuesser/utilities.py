#from qgis.gui import QgsMapTool
from PyQt5 import uic, QtWidgets, QtGui
from PyQt5.QtCore import pyqtSignal
from qgis.core import QgsProject, QgsCoordinateReferenceSystem, QgsCoordinateTransform
from osgeo import ogr, osr
import os, warnings

def coorTransform( pos, crsSrc,projectInstance):

    """coordinate transform using qgis"""
    crsDest = QgsCoordinateReferenceSystem(4326)
    #todo http://osgeo-org.1560.x6.nabble.com/QGIS-Developer-QGIS3-QgsCoordinateTransform-Error-td5347648.html
    xform = QgsCoordinateTransform(crsSrc, crsDest,projectInstance)
    pos = xform.transform(pos)
    return (pos.x(), pos.y())


def ogrCoorTransform (point, inSpatialRef):
    """transorms to geo wgs84 using ogr. inputs are OGRPoint point and the layer SpatialRef.
    output is float (x,y) as a tuple
    """
    outSpatialRef = osr.SpatialReference()
    outSpatialRef.ImportFromEPSG(4326)
    coordTrans = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)
    #http://gdal.org/python/osgeo.ogr.Geometry-class.html
    clonepoint = point.Clone()
    clonepoint.Transform(coordTrans)
    return (clonepoint.GetX(),clonepoint.GetY())
