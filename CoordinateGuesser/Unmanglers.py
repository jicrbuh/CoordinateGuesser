import osr

class Unmangler:
    def __init__(self,xUnmangler, yUnmangler = None):
        if yUnmangler is None:
            yUnmangler = xUnmangler
        self.x = xUnmangler
        self.y = yUnmangler
    def can(self,x,y):
        ret, cx = self.x.can(x)
        if ret == -1 or ret == 1:
            return False, None, None
        ret, cy = self.y.can(y)
        if ret == -1 or ret == 0:
            return False, None, None
        return True, cx, cy
    def toCor(self,x,cx,y,cy):
        return self.x.toHalfCor(x, cx), self.y.toHalfCor(y, cy)
    def __str__(self):
        if self.x == self.y:
            halcore = str(self.x)
        else:
            halcore = "x: "+str(self.x)+", y: "+str(self.y)
        return "regular WGS84GEO; submanglers: "+halcore

class UtmUnmangler (Unmangler):
    def __init__(self, projstring, xUnmangler, yUnmangler=None):
        Unmangler.__init__(self, xUnmangler, yUnmangler)
        self.projstring = projstring
    def toCor(self,x,cx,y,cy):
        ux, uy = Unmangler.toCor(self,x,cx,y,cy)
        return self.convertToGeo(ux,uy)
    def convertToGeo(self,ux,uy):
        destproj = osr.SpatialReference()
        destproj.ImportFromProj4("+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs")
        sourceproj = osr.SpatialReference()
        sourceproj.ImportFromProj4(self.projstring)

        transform = osr.CoordinateTransformation(sourceproj, destproj)
        t = transform.TransformPoint(ux, uy)
        dx, dy, _ = t
        return dx, dy
    def __str__(self):
        if self.x == self.y:
            halcore = str(self.x)
        else:
            halcore = "x: " + str(self.x) + ", y: " + str(self.y)
        return "projection converter mangler from projection ("+ self.projstring +"); submanglers: " + halcore

class UtmBiasedUnmangler(UtmUnmangler):
    def __init__(self, xoffset, yoffset, projstring, xUnmangler, yUnmangler=None):
        UtmUnmangler.__init__(self, projstring, xUnmangler, yUnmangler)
        self.yoffset = yoffset
        self.xoffset = xoffset
    def toCor(self,x,cx,y,cy):
        ux, uy = Unmangler.toCor(self, x, cx, y, cy)
        ux += self.xoffset
        uy += self.yoffset
        return self.convertToGeo(ux, uy)
    def __str__(self):
        if self.x == self.y:
            halcore = str(self.x)
        else:
            halcore = "x: " + str(self.x) + "; y: " + str(self.y)
        return "projection converter mangler from projection ("+ self.projstring +") with biases ({}; {}); submanglers: ".format(self.xoffset,self.yoffset) + halcore

class InverterUnmangler:
    def __init__(self, base):
        self.base = base
    def can(self,x,y):
        return self.base.can(y,x)
    def toCor(self, x, cx, y, cy):
        return self.base.toCor(y,cx,x,cy)
    def __str__(self):
        return "Inverted unmangler of "+str(self.base)