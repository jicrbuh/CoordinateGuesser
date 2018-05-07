from .halfCorUnmanglers import *
from .unmanglerGenerator import *
#from geographiclib.geodesic import Geodesic
from ogr import Geometry, wkbPoint
from .normalize import normalize
from pyproj import Geod
import osr, math
import warnings

def genUnmanglers(additionalutmprojs):
    dest = []
    utmHalfcors = [identUTM()]
    #utmgens = [utmBiasedGen(0,0,36),utmBiasedGen(0,0,37)]
    #todo the next lines makes the guesses wrong
    #trying to commit a change
    offsets = [i*1000000 for i in range(1,10)]
    zones = range(1,61)
    utmgens = [utmBiasedGen(0,0,i) for i in zones]
    utmEastingLMDigit = [utmBiasedGen(i,0,j) for i in offsets for j in zones]
    utmgens = utmgens+utmEastingLMDigit
    for aup in additionalutmprojs:
        print(str(aup))
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
    geohalfcors = [concattedDMS(),identDMS(),identDecDegGeo(), identDecMinGeo(), identDecSecGeo()]
    for gen in [geoGen()]:
        for u in gen(*geohalfcors):
            dest.append(u)
    return dest

def dist(p1, p2, transform):
    op = Geometry(wkbPoint)
    op.AddPoint(*p1)
    op.TransformTo(transform)
    #print("distance: " + str(op.Distance(p2)))
    return op.Distance(p2)

def distInMeters(p1, p2, transform,approxPoint):
    x1,y1=p1[0],p1[1]

    x2,y2=p2[0],p2[1]
    g = Geod(ellps='WGS84')  # Use WGS84
    distance =1
    try:
       az12, az21, distance = g.inv(x1, y1, x2, y2) #put in try\except
    except ValueError:
     #   #Geo = Geodesic.WGS84
      #  #dist = Geo.Inverse(x1, y1, x2, y2)
        distance = 110574*dist(p1, approxPoint, transform)
        #print("approx distance: " + str(distance))
    return distance

#inp - string divided by \t or tuple
"""inp = tuple,string"""
def Parse(inp, approxPoint = None, additionalprojs = [],delimiter = '[\t,]'):
    if isinstance(inp, str):
        inp = re.split(delimiter,inp,1)
    ix, iy = inp
    ix = normalize(ix)
    iy = normalize(iy)
    unmanglers = genUnmanglers(additionalprojs)
    suspects = []
    for u in unmanglers:
        can, cx, cy = u.can(ix,iy)
        if not can:
            continue
        suspects.append((u.toCor(ix,cx,iy,cy), str(u)))

    if approxPoint is None:
        return suspects

    destproj = osr.SpatialReference()
    destproj.ImportFromProj4("+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs")
    tupleAppPoint=approxPoint
    ap = Geometry(wkbPoint)
    ap.AddPoint(*approxPoint)

    ap.TransformTo(destproj)
    approxPoint = ap

    dsuspects = []
    for s,u in suspects:
        #d = distInMeters(s,tupleAppPoint,destproj,approxPoint) #destproj is wgs84 geo
        d = dist(s, approxPoint, destproj)
        dsuspects.append((s,u,d))

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
