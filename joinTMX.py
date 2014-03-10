#!/bin/python
"""
 Copyright 2014 Alexandre Lopes <aalopes@ovi.com>

 joinTMX.py - the objective of this script is to join all maps of a
 given area. To do so we use some information already published
 on TMW forums.
 Although not necessary, and actually less efficient, we use numpy
 arrays to store the CSV data in the .TMX files. For me this keeps
 things simpler.
 We use ElementTree to parse XML. What are usually called nodes
 are therefore called elements.

 We also use matrix-like coordinates for the CSV data, so 
 (rows, columns), which in coordinates correspond to (y, x). This 
 is because we use numPy arrays.
 ----------------------------------------------------------------------

 This particular file is not part of any other program, although a
 version of it has been released as part of The Mana World
 under GPL2
 
 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 2 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import xml.etree.ElementTree as ET
import numpy
from StringIO import StringIO # for string that behaves like a file object

# Constants
MAPS_DIR = './maps'

# Max number of tiles per tileset
MAX_TILES = 512

class BigMap:

    """
        Class for creating a big map which will contain all the smaller
        maps superimposed
    """

    def __init__(self,  width, height, name):
        """
            Constructor
        """
        self.height  = height
        self.width   = width
        self.name    = name
        self.layers  = {}    # dictionary containing layers and tiles for each 
        self.objects = []    # list containing objects as ElementTree elements 
        self.tileSets= {}    # dictionary containing tilesets as {"path": firstgid}
                                                                # we reserve firstgid=1 for collisions
                                                                # note: this needs to be changed to be path independent
        # we create already the collision layer, since we want to fill this in
        # with 2's (all is a collision) and not 0's (no tile) unlike the other layers
        # the reason for this is that I originally wrote this for The Mana World
        # if you don't need this (or don't have such layer), you can comment this
        self.layers['Collision'] = numpy.zeros((self.height,self.width)) 
        self.layers['Collision'].fill(2)

        # create base XML data - I guess this should be the last thing we make!
        # That way we already have all tiles in the XML file!
        # self.makeXML()

    def putMap(self, sMap):
        """
            Method for putting a smaller map into the big map
            It takes care of tilesets, layers and objects
        """
        # first we take care of the tilesets clashes
        # we do it like this, we assume a maximum tileset size
        # so the firstgid's in the big map will be 1, MAX_TILES, 2*MAX_TILES, ...
        # we only have to remap the gid's in the small maps
        # we have two situations: the tileset is already in the bigmap
        # and so the re-maping must be done using a previous firstgid
        # or it doesn't exist, and we grab a new firstgid that is
        # equal to the maximum already used + MAX_TILES.
        smallGID    = [int(value) for value in sMap.tileSets.values()] # from str to int
        smallGID.sort()    # ordered firstgids in the small map

        # let's change the gid of the tiles in the small maps to its symmetric
        # this way we can distinguish an yet to replace gid from one that has 
        # been replaced and we avoid substituting a gid twice
        for layer in sMap.layers:
            sMap.layers[layer] = -sMap.layers[layer]
        

        for tileSet in sMap.tileSets:

            # if the the big map already contains ANY tileset
            if self.tileSets.values():

                bigFirstGID = [int(value) for value in self.tileSets.values()] # str to int 
                largestGID  = max(bigFirstGID) # largest firstgid in the big map
            # otherwise, we do something that may seems weird
            # but makes sense when one looks at the code that follows
            # the ideia is that largestGID + MAX_TILES = MAX_TILES + 1
            # so the lowest firstgid available for a tileset is MAX_TILES + 1
            # while we reserve firstgid = 1 for collisions
            else:

                largestGID = 1

            smallFirstGID = int(sMap.tileSets[tileSet])    # the first gid for this tileset

            # if the tileset is already in the big map
            if tileSet in self.tileSets.keys():

                bigFirstGID   = int(self.tileSets[tileSet])  # the first gid for this tileset

                # either the firstgid is the same, and we don't remap
                if smallFirstGID == bigFirstGID:
                    pass

                # or the firstgid is not the same and we must remap
                else:
                    # then we check whether it is the largest firstgid
                    pos = smallGID.index(int(sMap.tileSets[tileSet]))
                    # if it is...
                    if smallGID[pos] == smallGID[-1]:
                        # we just map the values like this:
                        # smallFirstGID -> bigFirstGID, ..., 
                        # smallFirstGID + MAX_TILES -> bigFirstGID + MAX_TILES
                        for layer in sMap.layers:
                            sMap.layers[layer] = self.reMap(sMap.layers[layer],
                            smallFirstGID, bigFirstGID, MAX_TILES)
                    # else we must grab the next one, so we don't substitute
                    # the gids of more tiles than what we want to
                    else:
                        nextGID = smallGID[pos+1]
                        for layer in sMap.layers:
                            sMap.layers[layer] = self.reMap(sMap.layers[layer],
                            smallFirstGID, bigFirstGID, nextGID - smallFirstGID)
            # the tileset is not yet in the big map
            else:

                # if it is a collision tileset we assign it the firstid = 1
                if tileSet.endswith("collision.tsx"):

                    largestGID = -MAX_TILES + 1
                # again we check to see whether it is the largest firstgid in
                # the small map
                pos = smallGID.index(int(sMap.tileSets[tileSet]))
                # if it is...
                if smallGID[pos] == smallGID[-1]:
                    # we just map the values like this:
                    # smallFirstGID -> largestGID + MAX_TILES, ..., 
                    # smallFirstGID + MAX_TILES -> largestGID + 2*MAX_TILES
                    for layer in sMap.layers:
                        sMap.layers[layer] = self.reMap(sMap.layers[layer],
                        smallFirstGID, largestGID + MAX_TILES, MAX_TILES)
                    # and we add the tileset information to the big map
                    self.tileSets[tileSet] = str(largestGID + MAX_TILES)
                # else we must grab the next one, so we don't substitute
                # the gids of more tiles than what we want to
                else:
                    nextGID = smallGID[pos+1]
                    for layer in sMap.layers:
                        sMap.layers[layer] = self.reMap(sMap.layers[layer],
                        smallFirstGID, largestGID + MAX_TILES, nextGID - smallFirstGID)
                        # and we add the tileset information to the big map
                        self.tileSets[tileSet] = str(largestGID + MAX_TILES)

        # we now put the map per se into the correct position on the
        # big map
        # we must do it layer-wise 
        # note that .layers[layer] is a numpy array.
        # also it may happen that the smal map, sMap,
        # if the big map already contains the layer, we add the data,
        # otherwise we begin by creating a blank layer
        for layer in sMap.layers:
            if layer in self.layers:
                self.layers[layer][sMap.y : sMap.y + sMap.height ,
                                   sMap.x : sMap.x + sMap.width  ] = numpy.absolute(sMap.layers[layer])
            else:
                # layer does not yet exist in the big map, so create it first
                self.layers[layer] = numpy.zeros((self.height,self.width)) 
                self.layers[layer][sMap.y : sMap.y + sMap.height ,
                               sMap.x : sMap.x + sMap.width  ] = numpy.absolute(sMap.layers[layer])

        # append all the objects
        self.objects = self.objects + sMap.objects

    def reMap(self, inArray, iVal, fVal, n):
        """
            Method for remapping values in a numpy array. We do a linear mapping
            of the form iVal -> fVal, ... iVal+n -> fVal+n.
            Note that the original values in the input array are 0, since this way
            calling this function twice over the same input, we don't do a wrong
            substitution
        """
        # begin by creating subsitution dictionary
        rule = {-(iVal+i):fVal+i for i in range(n)}
        # now do the replacement
        outArray = numpy.copy(inArray)
        for oldVal, newVal in rule.iteritems(): 
            outArray[inArray == oldVal] = newVal
        
        return outArray
    
    def makeXML(self):
        """
          Method for building the tree for the base XML data
        """
        baseXML = """
                  <map version="1.0" orientation="orthogonal" width="%s" height="%s" tilewidth="32" tileheight="32">
                    <properties>
                      <property name="name" value="%s"/>
                    </properties>
                  </map>
                  """ % (str(self.width),str(self.height),self.name)
        # create root from string
        self.root = ET.fromstring(baseXML)
        # we now create the tileset tags
        for tileSet in self.tileSets:
            tileSetEle = ET.Element("tileset",
                                   {"firstgid" : self.tileSets[tileSet],
                                    "source"   : tileSet}
                                   )
            # append element to root
            self.root.append(tileSetEle)
        # we now create the layers and fill the corresponding csv with 0's
        for layer in self.layers:
            # create layer element
            layerEle = ET.Element("layer", 
                                  {"name"  : layer,
                                   "width" : str(self.width),
                                   "height": str(self.height)} 
                                 )
            # create data sub-element
            data = ET.SubElement(layerEle, "data",
                                 {"encoding":"csv"}
                                 )
            # in the data sub-element add empty map. first convert array to CSV
            string = StringIO()
            numpy.savetxt(string, self.layers[layer], fmt='%d', delimiter=",", newline="\n")
            data.text = string.getvalue()
            # now, what happens is that it appears that Tiled requires a "," at the end of each
            # line, except the last one, so let us do it
            # also, the last line doesn't have a newline character
            data.text = data.text.rstrip()
            data.text = data.text.replace("\n",",\n")
            # append element to root
            self.root.append(layerEle)
            # data.text = createCSV("0",self.width,self.height)

        # we now append all objects - we append them to an object group
        # element, which we have to create
        objGroup = ET.Element("objectgroup",
                                   {"name"    : "Objects",
                                    "width"   : "0",
                                    "height"  : "0",
                                    "visible" : "0"
                                   }
                                  )
        for obj in self.objects:
            objGroup.append(obj)
        self.root.append(objGroup)
        # create tree from root
        self.tree = ET.ElementTree(self.root)
    def export(self,fileName):
        self.tree.write(fileName)

    def createCSV(self, inputStr, width, height):
        """
            Creates an array of widht x height 
            CSV where each element is equal to inputStr
            Note: I'm not using this method right now
        """
        ((inputStr + ",") * width + "\n") * height
        

class ParseMap:

    """
        Class for parsing and holding TMX map data
    
        Note: coordinates are tile based
        self.x - x coordinates of the upper-left hand corner of this map
        self.y - y coordinates of the upper-left hand corner of this map
    """

    def __init__(self, tmx, x, y):
        """
            Constructor
        """
        self.x = x
        self.y = y
        self.tree = ET.parse(tmx)
        self.root = self.tree.getroot()
        self.handleMap()

    def handleMap(self):
        """
            Method for handling map by extracting important attributes from
            the xml file
        """
        self.width    = int(self.root.attrib['width'])
        self.height   = int(self.root.attrib['height'])
        self.layers   = {} # this will hold all layers and the csv data in them 
        self.tileSets = {} # this will hold the firstgid and path to the tileset
        self.objects  = [] # this will hold the objects
        self.handleTileSets()
        self.handleLayers()
        self.handleObjects()
        #self.handleMapProperties()
        return

    def handleLayers(self):
        """
            Method for handling layers, extracting the CSV data from them
            and putting it into a numpy array.
            It updates the self.layers dictionary in the following form:
            {'layerName': tilesAsNumPyArray}
        """
        for layer in self.root.findall('layer'):
            # for each layer extract layer name and csv data
            name = layer.get('name')
            data = layer.find('data').text

            # now it appears that "Tiled" leaves a comma at the end of
            # each row, except the last one
            # this is a problem for numpy.genfromtxt, so we will
            # need to remove the trailing comas
            data = data.replace(',\n', '\n');

            # convert CSV data to numpy array
            # but first convert data to a file-like object
            dataArray = numpy.genfromtxt(StringIO(data), delimiter=',')
            self.layers[name] = dataArray

    def handleObjects(self):
        """
            Method for handling objects, storing them as ElementTree objects
            so we can then just use them on the big map. We also need to
            adjust the x and y coordinates of the objects given the map
            coordinates (we assume a tileSize = 32)
        """
        for obj in self.root.iter('object'):
            obj.attrib['x'] = str(int(obj.get('x')) + 32*self.x)
            obj.attrib['y'] = str(int(obj.get('y')) + 32*self.y)
            self.objects.append(obj)

    def handleTileSets(self):
        """
            Method for handling tilesets. We store the tileset path and the
            gid this way: {gid: path}
        """
        for tileSet in self.root.findall('tileset'):
            gid    = tileSet.get('firstgid')
            source = tileSet.get('source')
            self.tileSets[source] = gid

def parseFile(fileName):
    """
        Function to parse input file
        It returns data as a dictionary so it's easier to extract
        the relevant data

        tileSize - size of each tile in pixels
        nameBig  - name of the big map (or continent)
        sizeBig  - the size, in number of tiles, of the big map
        offset   - the offset so the first small map starts at (0, 0)
        mapData  - list of the form [[mapPath_1, mapCoordX_1, mapCoordY_1], 
                   [...], ...]
                   where mapPath_1 is the path for the first map and
                   mapCoordX_1 its X coordinates in the big map and the same
                   for Y.
    """
    f = open(fileName, 'r')

    mapData = []
    for line in f:
        line = line.rstrip()
        if line.startswith("tilesize"):
            # currently not using this property 
            data = line.split(" ")
            tileSize = data[1] 

        elif line.startswith("continent"):
            data      = line.split(" ")
            nameBig   = data[1]
            sizeBig   = [data[2], data[3]]
            width     = data[2]
            height    = data[3]

        elif line.startswith("offset"):
            data      = line.split(" ")
            offset    = [data[1], data[2]]

        elif line.startswith("map"):
            data      = line.split(" ")
            mapPath   = MAPS_DIR + "/" + data[1] + ".tmx"
            mapCoordX = data[2]
            mapCoordY = data[3]
            # append everything into our map data
            mapData.append([mapPath, mapCoordX, mapCoordY])
        else:
            pass
    return {"tileSize": tileSize, "nameBig": nameBig, "sizeBig": sizeBig, 
            "offset": offset, "mapData": mapData}

def main(argv):
    """
        Main function
        takes as argument a file with the maps coordinates and big map size
    """
    # argv handling
    if len(argv) < 2:
        sys.exit('Usage: %s file-name' % argv[0])
    if not os.path.exists(sys.argv[1]):
        sys.exit('ERROR: File %s not found!' % argv[1])

    # parse input file
    inData = parseFile(argv[1])
    # data - just to make it more readable
    bigWidth  = int(inData["sizeBig"][0])
    bigHeight = int(inData["sizeBig"][1])
    bigName   = inData["nameBig"]
    offsetX   = int(inData["offset"][0]) 
    offsetY   = int(inData["offset"][1]) 
    mapData   = inData["mapData"]
    
    # create BigMap instance
    bigMap =  BigMap(bigWidth, bigHeight, bigName) 

    # load maps and etc
    maps = []
    print "Parsing..."
    for smallMap in mapData:
        print "Parsing file " + smallMap[0]
        # append instance
        maps.append(ParseMap(smallMap[0], int(smallMap[1]) + offsetX, int(smallMap[2]) + offsetY))

    # now join all maps into the bigMap
    print "Joining maps..."
    mapNumber = 0 # counter for printing
    for smallMap in maps:
        print "Inserting " + mapData[mapNumber][0] + " data"
        bigMap.putMap(smallMap)
        mapNumber += 1

    # finally make the big map xml tree
    bigMap.makeXML()

    # and export it to a tiled-like xml file
    print "Exporting..."
    outFileName = MAPS_DIR + "/" + bigName + ".tmx"
    bigMap.export(outFileName)

    print "Done!"
if __name__ == '__main__':
    main(sys.argv)
