def escape(string):
    return string.replace('&', '&amp;')  \
                 .replace('<', '&lt;')   \
                 .replace('>', '&gt;')   \
                 .replace('"', '&#34;') \
                 .replace("'", '&#39;')


def internalcode(f):
    """Marks the function as internally used"""
    internal_code.add(f.__code__)
    return f


internal_code = set()


