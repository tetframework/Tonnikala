str = str


def escape(string):
    return (string.replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&#34;')
            .replace("'", '&#39;'))


def internalcode(f):
    """Marks the function as internally used"""
    internal_code.add(f.__code__)
    return f


class StringWithLocation(str):
    def __new__(cls, value: str, lineno, offset):
        val = str.__new__(cls, value)
        val.position = lineno, offset
        return val

    def __getslice__(self, start, end):
        return self.__getitem__(slice(start, end))

    def __getitem__(self, i):
        s = str(self)
        if isinstance(i, slice):
            start = i.indices(len(self))[0]
            position = calculate_position(s, start, self.position)
            return StringWithLocation(s[i], position[0], position[1])

        return s[i]


def calculate_position(source, offset, start=None):
    if start is None:
        start = (1, 0)

    fragment = source[:offset]
    lines = fragment.count('\n')
    column_offset = offset - fragment.rfind('\n') if lines else offset

    if lines:
        pos = start[0] + lines, column_offset
    else:
        pos = start[0], start[1] + column_offset

    return pos


internal_code = set()


def is_nonstr_iter(v):
    if isinstance(v, str):
        return False
    return hasattr(v, '__iter__')


def reraise(tp, value, tb=None):  # pragma: no cover
    if value is None:
        value = tp()
    if value.__traceback__ is not tb:
        raise value.with_traceback(tb)
    raise value
