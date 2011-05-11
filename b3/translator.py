# -*- coding: utf-8 -*-
# Translation table for non ascii chars
# Copyright (C) 2010-2011 Sergio Gabriel Teves
# 
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# 04-05-2011 - SGT
# Improved table

TRANSLATION_TABLE = {
    'a': (192, 198),
    'e': (200, 203),
    'i': (204, 207),
    '.': (209, 209),
    'o': (210, 216),
    'u': (217, 220),
    'a': (224, 230),
    'e': (232, 235),
    'i': (236, 239),
    'o': (242, 248),
    'u': (249, 252),
    '.': (241, 241)
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
        if ord_chr >= 128:
            charval = None
            for val, codes in TRANSLATION_TABLE.items():
                minc, maxc = codes
                if ord_chr >= minc and ord_chr <= maxc:
                    charval = val
                    break;
            if not charval:
                charval = '_'
            new_str += charval
        else:
            new_str += char
    return new_str.encode('utf-8')
    
if __name__ == "__main__":
    text = [u"Uberlândia", u"Araña", u"Papúa", u"áéíóú"]
    for t in text:
        print translate(t) + "\n"
