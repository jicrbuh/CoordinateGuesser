from .Unmanglers import *

"""
an unmalger generator is an object that can be called with a collection of halfCoorUnmanglers and return a collection of full unmanglers.
for each unmangler, its inverse unmangler is also included.
"""

#todo these shoulda just been functions

class utmBiasedGen:
    """
    generates biased UTM unmanglers through offsets and projections provided at construction time.
    """
    def __init__(self, xoff, yoff, proj):
        self.xoff = xoff
        self.yoff = yoff
        if isinstance(proj, str):
            self.proj = proj
        else:
            self.proj = "+proj=utm +zone={} +ellps=WGS84 +datum=WGS84 +units=m +no_defs".format(proj)
    def __call__(self, *halfcors):
        #todo join here, also star is uncessacry
        for halfcor in halfcors:
            ret = UtmBiasedUnmangler(self.xoff,self.yoff,self.proj,halfcor, halfcor)
            yield ret
            yield InverterUnmangler(ret)

class geoGen:
    """
    generates simple unmanglers.
    """
    def __init__(self):
        pass
    def __call__(self, *halfcors):
        #todo join here, also star is uncessacry
        for halfcor in halfcors:
            ret = Unmangler(halfcor,halfcor)
            yield ret
            yield InverterUnmangler(ret)