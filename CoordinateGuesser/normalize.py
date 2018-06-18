import re

def fixdmschars(dms_str):
    """
    replaces all wierd characters in geo strings with appropriate ones
    :param dms_str: the string with wierd charaters
    :return: the same string with all wierd charaters replaced with teh "standard" charaters
    """
    dx = [0x0064, 0x00B0, 0x0044] #d, °, D
    mx = [0x006D, 0x00b4, 0x0027,0x2032,0x2035,0x02B9,0x2019,0x02BC,0x02BC,0x055A,0xA78B,0xA78C,0xFF07,0x004d] #m, ´, ', ′, ‵, ʹ, ’, ʼ, ʼ, ՚, Ꞌ, ꞌ, ＇, M
    sx = [0x0022, 0x2033, 0x2036, 0x02BA, 0x02EE, 0x201d, 0x201c, 0x201F, 0xFF02] # ", ″, ‶, ʺ, ˮ, ”
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