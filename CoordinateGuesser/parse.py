from .halfCorUnmanglers import *
from .unmanglerGenerator import *
from ogr import Geometry, wkbPoint
from .normalize import normalize
import osr
import warnings

def genUnmanglers(additionalutmprojs):
    dest = []
    utmHalfcors = [identUTM()]
    #utmgens = [utmBiasedGen(0,0,36),utmBiasedGen(0,0,37)]
    #todo the next lines makes the guesses wrong
    utmgens = [utmBiasedGen(0,0,i) for i in range(1,61)]
    for aup in additionalutmprojs:
        if isinstance(aup,int) or len(aup) == 1:
            aup = (0,0,aup)
        utmgens.append(utmBiasedGen(*aup))
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

    return op.Distance(p2)

#todo make this more visible
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
    #todo does that mean that the distance is always in meters?
    destproj = osr.SpatialReference()
    destproj.ImportFromProj4("+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs")

    ap = Geometry(wkbPoint)
    ap.AddPoint(*approxPoint)

    ap.TransformTo(destproj)
    approxPoint = ap

    dsuspects = []
    for s,u in suspects:
        d = dist(s,approxPoint,destproj) #dest proj
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
