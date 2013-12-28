def escape(string):
    return string.replace('&', '&amp;')  \
                 .replace('<', '&lt;')   \
                 .replace('>', '&gt;')   \
                 .replace('"', '&#34;') \
                 .replace("'", '&#39;')

