class ParseError(Exception):
    def __init__(self, message, charpos):
        super(ParseError, self).__init__(message)
        self.charpos = charpos
