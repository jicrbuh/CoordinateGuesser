import re

def fixdmschars(dms_str):
    """
    replaces all wierd characters in geo strings with appropriate ones
    :param dms_str: the string with wierd charaters
    :return: the same string with all wierd charaters replaced with teh "standard" charaters
    """

    dx = ['d', '°', 'D'] #d, °, D
    mx = ['m', '´', "'", '′', '‵', 'ʹ', '’', 'ʼ', 'ʼ', '՚', 'Ꞌ', 'ꞌ', '＇', 'M'] #m, ´, ', ′, ‵, ʹ, ’, ʼ, ʼ, ՚, Ꞌ, ꞌ, ＇, M
    sx = ['"', "''", '"', '＂', '〃', 'ˮ',  '᳓', '″',  '‶', '˶', 'ʺ', '“', '”', '˝', '‟'] # ",'', ", ＂, 〃, ˮ, ᳓, ″, ‶, ˶, ʺ, “, ”, ˝, ‟

    w = ['W', 'O', 'w', 'o']
    e = ['E', 'L', 'e', 'l']
    s = ['S', 's']
    n = ['N', 'n']
    l = [dx, mx, sx, w, e, s, n]
    #print dms_str
    mystr = dms_str
    for r in l:
        o = ord(r[0])
        x0 = chr(o)
        for x in r[1:]:
            mystr = mystr.replace(x, x0,1)
    return mystr

def extractSignfromGeo(x):
    """
    tries to extract a direction sign from a geo coordinate string
    :param x: the string to parse
    :return: a tuple containing (the string without the direction token, the sign of the direction, the direction index 0-x; 1-y; 2-no direction found)
    """
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