# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


class ParseError(Exception):
    def __init__(self, message, charpos):
        super(ParseError, self).__init__(message)
        self.charpos = charpos
