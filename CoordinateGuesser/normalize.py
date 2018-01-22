import re

def fixdmschars(dms_str):
    dx = [0x0064, 0x00B0, 0x0044]
    mx = [0x006D, 0x00b4, 0x0027,0x2032,0x2035,0x02B9,0x2019,0x02BC,0x02BC,0x055A,0xA78B,0xA78C,0xFF07,0x004d]
    sx = [0x0022, 0x2033,0x2036,0x02BA,0x02EE, 0x201d]
    ds = [chr(x) for x in dx]
    ms = [chr(x) for x in mx]
    ss = [chr(x) for x in sx]
    w = ['W', 'O', 'w', 'o']
    e = ['E', 'L', 'e', 'l']
    s = ['S', 's']
    n = ['N', 'n']
    l = [ds, ms, ss, w, e, s ,n]
    #print dms_str
    str = dms_str
    for r in l:
        o = ord(r[0])
        x0 = chr(o)
        for x in r[1:]:
            str = str.replace(x, x0,1)
    return str

def normalize(x):
    x = fixdmschars(x)
    #x = re.sub(r'[\s,/\\]+', ' ', x,3)
    return x

def extractSignfromGeo(x):
    if re.search("[sS]", x):
        sign = -1
        pos = 1
    elif re.search("[wW]", x):
        sign = -1
        pos = 0
    elif re.search("[nN]", x):
        sign = 1
        pos = 1
    elif re.search("[eE]", x):
        sign = 1
        pos = 0
    else:
        sign = 1
        pos = 2
    if x.startswith('-'):
        sign*=-1
        x = x[1:]
    return re.sub('[swenSWENolOL]', '', x, 1),sign,pos