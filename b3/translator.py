# -*- coding: utf-8 -*-

TRANSLATION_TABLE = {
    228: 'a', # ä
    235: 'e', # ë
    239: 'i', # ï
    246: 'o', # ö
    252: 'u', # ü
    225: 'a', # á
    233: 'e', # é
    237: 'i', # í
    243: 'o', # ó
    250: 'u', # u
    241: '.', # ñ
    232: 'e', # è
    227: 'a', # ã
}

def translate(text):
    # lets try to decode the string is unicode
    try:
        text = text.decode('utf-8')
    except Exception:
        pass

    new_str = ""
    for char in text:
        ord_chr = ord(char)
        if ord_chr in TRANSLATION_TABLE:
            new_str += TRANSLATION_TABLE[ord_chr]
        else:
            new_str += char
    return new_str.encode('utf-8')
