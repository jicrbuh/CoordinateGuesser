import os
import io
import chardet
import codecs


def get_encoding_by_bom(filename):
    bytes = min(32, os.path.getsize(filename))
    raw = open(filename, 'rb').read(bytes)

    result = chardet.detect(raw)
    print(result)
    encoding = result['encoding']
    return encoding


def read_txt_by_bom(filename, encoding):
    if encoding is None:
        encoding = get_encoding_by_bom(filename)
    infile = io.open(filename, 'r', encoding=encoding)
    data = infile.read()
    infile.close()
    return data, encoding

