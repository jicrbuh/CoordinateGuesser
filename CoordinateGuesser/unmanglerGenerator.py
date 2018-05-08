from .Unmanglers import *

class utmBiasedGen:
    def __init__(self, xoff, yoff, proj):
        self.xoff = xoff
        self.yoff = yoff
        if isinstance(proj, str):
            self.proj = proj
        else:
            self.proj = "+proj=utm +zone={} +ellps=WGS84 +datum=WGS84 +units=m +no_defs".format(proj)
    def __call__(self, *halfcors):
        for halfcor in halfcors:
            #todo needs to add somehow the invertedbiasedunamnalger
            ret = UtmBiasedUnmangler(self.xoff,self.yoff,self.proj,halfcor, halfcor)
            yield ret
            yield InverterUnmangler(ret)

class geoGen:
    def __init__(self):
        pass
    def __call__(self, *halfcors):
        for halfcor in halfcors:
            ret = Unmangler(halfcor,halfcor)
            yield ret
            yield InverterUnmangler(ret)