# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CoordGuesser
                                 A QGIS plugin
 Parse, unscumble, guess coordinates
                             -------------------
        begin                : 2017-10-19
        copyright            : (C) 2017 by Idan Miara
        email                : idan@miara.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load CoordGuesser class from file CoordGuesser.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .CoordGuesser import CoordGuesser
    return CoordGuesser(iface)
