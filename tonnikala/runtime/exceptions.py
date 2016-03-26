class TemplateError(Exception):
    pass


class TemplateSyntaxError(TemplateError):
    """Raised to tell the user that there is a problem with the template."""

    def __init__(self, message, lineno=None, name=None,
                 source=None, filename=None, node=None):
        TemplateError.__init__(self, message)
        self.message = message

        self.lineno = lineno
        if lineno is None and node is not None:
            self.lineno = getattr(node, 'position', (1, 0))[0]

        self.name = name
        self.filename = filename
        self.source = source

        # this is set to True if the debug.translate_syntax_error
        # function translated the syntax error into a new traceback
        self.translated = False

    def __str__(self):
        # for translated errors we only return the message
        if self.translated:
            return self.message

        # otherwise attach some stuff
        location = 'line %d' % self.lineno
        name = self.filename or self.name

        if name:
            location = 'File "%s", %s' % (name, location)
        lines = [self.message, '  ' + location]

        # if the source is set, add the line to the output
        if self.source is not None:
            try:
                line = self.source.splitlines()[self.lineno - 1]
            except IndexError:
                line = None
            if line:
                lines.append('    ' + line.strip())

        return u'\n'.join(lines)
