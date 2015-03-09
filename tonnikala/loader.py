from tonnikala import expr
from tonnikala.languages import javascript
from tonnikala.syntaxes.tonnikala import parse as parse_tonnikala, parse_js as parse_js_tonnikala
from tonnikala.syntaxes.chameleon import parse as parse_chameleon
from tonnikala.syntaxes.jinja2 import parse as parse_jinja2
from os import path
from tonnikala.languages.python.generator import Generator as PythonGenerator
from tonnikala.languages.javascript.generator import Generator as JavascriptGenerator
from tonnikala.runtime import python
import six
import codecs
import os
from errno import ENOENT
import time


MIN_CHECK_INTERVAL = 0.25

if six.PY3:
    import builtins as __builtin__
else:
    import __builtin__

class Helpers():
    pass

escape = python.escape

helpers = Helpers()
helpers.literal  = lambda x: x
helpers.gettext  = lambda x: x
helpers.egettext = lambda x: escape(x)

def get_builtins_with_chain(chain=[ helpers ]):
    builtins = {}
    for i in [ __builtin__ ] + list(reversed(chain)):
        for j in dir(i):
            if not j.startswith('__') and not j.endswith('__'):
                builtins[j] = getattr(i, j)

    return builtins

_builtins = None
def get_builtins():
    global _builtins
    if _builtins is None:
        _builtins = get_builtins_with_chain()

    return _builtins

NOT_FOUND = object()

def make_template_context(context):
    rv = get_builtins().copy()
    rv.update(context)
    return rv


class Template(object):
    def __init__(self, binder):
        self.binder_func = binder

    def bind(self, context):
        self.binder_func(context)

    def render_to_buffer(self, context, funcname='__main__'):
        context = make_template_context(context)
        self.bind(context)
        return context[funcname]()

    def render(self, context, funcname='__main__'):
        return self.render_to_buffer(context, funcname).join()


parsers = {
    'tonnikala':    parse_tonnikala,
    'js_tonnikala': parse_js_tonnikala,
    'chameleon':    parse_chameleon,
    'jinja2':       parse_jinja2
}


class Loader(object):
    def __init__(self, debug=False, syntax='tonnikala'):
        self.debug = debug
        self.syntax = syntax

    def load_string(self, string, filename="<string>"):
        parser_func = parsers.get(self.syntax)
        if not parser_func:
            raise ValueError("Invalid parser syntax %s: valid syntaxes: %r"
                % sorted(parsers.keys()))

        tree = parser_func(filename, string)
        code = PythonGenerator(tree).generate_ast()

        if self.debug:
            import ast

            print(ast.dump(code))

            try:
                import astor
                print(astor.codegen.to_source(code))
            except ImportError:
                print("Not reversing AST to source as astor was not installed")


        runtime = python.TonnikalaRuntime()
        runtime.loader = self

        glob = {
            '__TK__runtime': runtime,
            'literal':     lambda x: x
        }

        compiled = compile(code, '<string>', 'exec')
        exec(compiled, glob, glob)
        template_func = glob['__TK__binder']
        return Template(template_func)


class FileLoader(Loader):
    def __init__(self, paths=[], debug=False, syntax='tonnikala'):
        super(FileLoader, self).__init__(debug=debug, syntax=syntax)

        self.cache = {}
        self.paths = list(paths)
        self.reload = False
        self.last_reload_check = time.time()

    def add_path(self, *a):
        self.paths.extend(a)

    def resolve(self, name):
        if os.path.isabs(name):
            if os.path.exists(name):
                return name

        for i in self.paths:
            path = os.path.abspath(os.path.join(i, name))
            if os.path.exists(path):
                return path

        return None

    def set_reload(self, flag):
        self.reload = flag

    def check_reload(self):
        if self.last_reload_check + MIN_CHECK_INTERVAL > time.time():
            return

        for name, tmpl in list(self.cache.items()):
            if not os.stat(tmpl.path):
                self.cache.pop(name)
                continue

            if os.stat(tmpl.path).st_mtime > tmpl.mtime:
                self.cache.pop(name)
                continue

        self.last_reload_check = time.time()

    def load(self, name):
        if self.reload:
            self.check_reload()

        template = self.cache.get(name)
        if template:
            return template

        path = self.resolve(name)
        if not path:
            raise OSError(ENOENT, "File not found: %s" % name)

        with codecs.open(path, 'r', encoding='UTF-8') as f:
           contents = f.read()
           mtime = os.fstat(f.fileno()).st_mtime

        template = self.load_string(contents, filename=path)
        template.mtime = mtime
        template.path  = path

        self.cache[name] = template
        return template


class JSLoader(object):
    def __init__(self, debug=False, syntax='js_tonnikala', minify=False):
        self.debug = debug
        self.syntax = syntax
        self.minify = minify

    def load_string(self, string, filename="<string>"):
        parser_func = parsers.get(self.syntax)
        if not parser_func:
            raise ValueError("Invalid parser syntax %s: valid syntaxes: %r"
                % sorted(parsers.keys()))

        tree = parser_func(filename, string)
        code = JavascriptGenerator(tree).generate_ast()

        if self.debug:
            print("JS template output code for %s" % filename)
            print(code)

        if self.minify:
            from slimit import minify
            code = minify(code, mangle=True)

        return code
