# CoordinateGuesser

This plugin parses misstyped or scrambled coordinates from different projections to WGS84-Geo.
For example, DMS and partial DMS (148 - 11' 7", 23 - 29' 24"), Commas instead of points (40°38'51,14", 40°38'50,67"), UTM without a zone 
and missing the leftmost digit (?90950,3431318.8)

For example, if you have this scarmbled coordinate (x,y) and a general guess of the area they should map to: (x',y'),
the plugin will give you the best result for the unmangled coordinate, chosen by the shortest distance to the guess.

If you don't know to which area the coordinate should map, you can choose the "No Given Guess" option, but the result will be chosen randomly, so it is not reccomended.
The guess can be chosen by clicking on the map (By a given Long, Lat) or by choosing a feature in layer (By a centroid of a feature from layer).


### Batch Mode
If you have a list of scrambled coordinates, you can use the Batch Mode option, by choosing a .csv file that has in each row a different coordinate, 
so the first column contains the x coordinate, and the second contains the y coordinate. 
If you choose using a guess (By a given Long, Lat or By a centroid of a feature from layer), it will be uniform to all of the points in the file.
This is unless you choose the option "Attribute choice in file" and then for each row, the third column will contain the name of the attribute,
and the guess will be different for every scarmbled coordinate, and will be chosen by the centroid of the matching feature (if exists).
#### Batch Mode Example
For example, use the batch mode with the example file in the plugin folder (/help/example/example_ny_boroughs.csv).   
The file is in the format:  
_mangled X_, _mangled Y_, _Attribute_  
* Open Qgis and open the example .shp file (/help/example/ny_boroughs.shp) in a new project.  
* Open Coordinate Guesser and fill the preferences as in the picture (the .csv file path may be different on your computer):  
![Preferenced for the example](https://github.com/jicrbuh/CoordinateGuesser/blob/master/help/example/CoorGuesser_batch_example.png)  

* press "Go!"
