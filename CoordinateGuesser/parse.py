from .halfCorUnmanglers import *
from .unmanglerGenerator import *
#from geographiclib.geodesic import Geodesic
from ogr import Geometry, wkbPoint
from .normalize import fixdmschars
from pyproj import Geod
import osr, math
import warnings


def genUnmanglers(additionalprojs,ix,iy):
    """
    generate a collection of unmanglers
    :param additionalutmprojs: by default, only the 36 and 37 UTM zones are considered, other zones can be entered here or a tuple with offests. (100,20,36) will add an unmamgler to zone 36 which adds 100 to x and 20 to y.
    :return: a list of unmanglers generated from the input
    """
    dest = []
    utmHalfcors = [identUTM()]

    offsets = [i*1000000 for i in range(1,10)]
    utmEastingLMDigit = []
    utmNorthingLMDigit = []
    zones = range(1,61)
    utmgens = [utmBiasedGen(0, 0, i) for i in zones]
    if all([ix, iy]):  # if genUnmanglers
        try:
            ix_int_string = str(int(float(ix)))
            iy_int_string = str(int(float(iy)))
            leng_ix=len(ix_int_string)
            leng_iy=len(iy_int_string)
            power_ten_x = pow(10, leng_ix)
            power_ten_y = pow(10, leng_iy)
            xoffsets = [i*power_ten_x  for i in range(1, 10)]
            yoffsets = [i*power_ten_y for i in range(1, 10)]
            utmEastingLMDigit = [utmBiasedGen(i, 0, j) for i in xoffsets for j in zones]
            utmNorthingLMDigit = [utmBiasedGen(0, i, j) for i in yoffsets for j in zones]

        except ValueError:
            pass

    utmgens = utmgens + utmEastingLMDigit + utmNorthingLMDigit
    for aup in additionalprojs:

       # if isinstance(aup,int) or len(aup) == 1:
         #   aup = (0,0,aup)
       # else isinstance(aup,string):
        #    aup=(0,0,aup)
        aup =(0,0,aup)
        utmgens.append(utmBiasedGen(*aup))
        #utmgens.append(utmBiasedGen(aup)) #chen
    for gen in utmgens:
        for u in gen(*utmHalfcors):
            dest.append(u)
    #todo make a repository for all these types
    geohalfcors = [concattedDMS(), identDMS(), identDecDegGeo(), identDecMinGeo(), identDecSecGeo()]
    for gen in [geoGen()]:
        for u in gen(*geohalfcors):
            dest.append(u)
    return dest

def dist(p1, p2, transform):
    """
    get distance between two points according to a transformation
    NOTE: since we only use the distance to cmopare to other distances, the actual units is incosequential
    :param p1: the first point
    :param p2: the second point
    :param transform: the destionation projection to use
    :return: the distance between the two points, in the selected transformation
    """
    op = Geometry(wkbPoint)
    op.AddPoint(*p1)
    op.TransformTo(transform)

    return op.Distance(p2)


def distInMeters(p1, p2, transform, approxPoint):
    x1, y1 = p1[0], p1[1]
    x2, y2 = p2[0], p2[1]
    # print('distance between {},{} and {},{}'.format(x1, y1, x2, y2))
    g = Geod(ellps='WGS84')  # Use WGS84
    try:
        az12, az21, distance = g.inv(x1, y1, x2, y2)
        # print("exact distance (km): " + str(distance / 1000))
    except ValueError:
     #   #Geo = Geodesic.WGS84
      #  #dist = Geo.Inverse(x1, y1, x2, y2)
        distance = 110574*dist(p1, approxPoint, transform)
        # print("approx distance (km): " + str(distance/1000))
    return distance


# todo make this more visible
def Parse(inp, approxPoint = None, additionalprojs = [], delimiter = '[\t,]'):
    """
    attempts to parse the input string into likely points
    :param inp: the mangled coordinate string
    :param approxPoint: if provided, the candidates will be sorted according to distance to this point
    :param additionalprojs: additional projections to consider, check genUnmanglers's doc for additional info.
    :return: a list of potiental unmangled coordinates, along with the unmnaglers that unmangled it. If approxPoint is provided, each point will also have the distance to it.
    """
    if additionalprojs is None:
        additionalprojs = []
    if isinstance(inp, str):
        inp = re.split(delimiter, inp, 1)
    ix, iy = inp
    ix = fixdmschars(ix)
    iy = fixdmschars(iy)
    unmanglers = genUnmanglers(additionalprojs, ix, iy)
    #print(*unmanglers, sep='\n')
    suspects = []
    for u in unmanglers:
        can, cx, cy = u.can(ix, iy)
        if not can:
            continue
        # check if y is between -90 and 90. if not then can = False
        realx, realy = u.toCor(ix, cx, iy, cy)
        if realy > 90 or realy < -90:
            continue
        suspects.append((u.toCor(ix, cx, iy, cy), str(u)))

    if approxPoint is None:
        return suspects

    destproj = osr.SpatialReference()
    destproj.ImportFromProj4("+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs")
    tupleAppPoint = approxPoint
    ap = Geometry(wkbPoint)
    ap.AddPoint(*approxPoint)

    ap.TransformTo(destproj)
    approxPoint = ap

    dsuspects = []
    for s, u in suspects:
        d = distInMeters(s,tupleAppPoint,destproj,approxPoint)  # destproj is wgs84 geo
        #d = dist(s, approxPoint, destproj)
        dsuspects.append((s, u, d))

    dsuspects.sort(key=lambda a:a[-1])
    return dsuspects



def decToDms(dec, secdigits = 3):
    if dec < 0:
        return "-"+decToDms(-dec)
    d = dec - (dec%1)
    dec = (dec-d)*60
    m = dec - (dec%1)
    dec = (dec-m)*60
    s = dec
    return ('''{:.0f}° {:.0f}′ {:.'''+str(secdigits)+'''f}″''').format(d,m,s)

def decToDmsCoor(x,y, secdigits = 3):
    return "({}, {})".format(decToDms(x,secdigits),decToDms(y,secdigits))
