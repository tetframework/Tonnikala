def escape(string):
    return string.replace('&', '&amp;')  \
                 .replace('<', '&lt;')   \
                 .replace('>', '&gt;')   \
                 .replace('"', '&quot;') \
                 .replace("'", '&#39;') 

