import errno
import sys
import time

import codecs
import os

from .compat import reraise
from .languages.javascript.generator import Generator as JavascriptGenerator
from .languages.python.generator import Generator as PythonGenerator
from .runtime import python, exceptions
from .syntaxes.chameleon import parse as parse_chameleon
from .syntaxes.tonnikala import parse as parse_tonnikala, \
    parse_js as parse_js_tonnikala

_make_traceback = None
MIN_CHECK_INTERVAL = 0.25

try:  # pragma: python3
    import builtins as __builtin__
except ImportError:  # pragma: python2
    # noinspection PyUnresolvedReferences,PyCompatibility
    exec('import __builtin__')


class Helpers():
    pass


escape = python.escape

helpers = Helpers()
helpers.literal = lambda x: x
helpers.gettext = lambda x: x
helpers.egettext = lambda x: escape(x)


def get_builtins_with_chain(chain=[helpers]):
    builtins = {}
    for i in [__builtin__] + list(reversed(chain)):
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


_NO = object()


def handle_exception(exc_info=None, source_hint=None, tb_override=_NO):
    """Exception handling helper.  This is used internally to either raise
    rewritten exceptions or return a rendered traceback for the template.
    """

    global _make_traceback
    if exc_info is None:  # pragma: no cover
        exc_info = sys.exc_info()

    # the debugging module is imported when it's used for the first time.
    # we're doing a lot of stuff there and for applications that do not
    # get any exceptions in template rendering there is no need to load
    # all of that.
    if _make_traceback is None:
        from .runtime.debug import make_traceback as _make_traceback

    exc_type, exc_value, tb = exc_info
    if tb_override is not _NO:  # pragma: no cover
        tb = tb_override

    traceback = _make_traceback((exc_type, exc_value, tb), source_hint)
    exc_type, exc_value, tb = traceback.standard_exc_info
    reraise(exc_type, exc_value, tb)


class Template(object):
    handle_exception = staticmethod(handle_exception)

    def __init__(self, binder):
        self.binder_func = binder

    def bind(self, context):
        self.binder_func(context)

    def render_to_buffer(self, context, funcname='__main__'):
        try:
            context = make_template_context(context)
            self.bind(context)
            return context[funcname]()

        except Exception as e:
            exc_info = sys.exc_info()

        try:
            self.handle_exception(exc_info)
        finally:
            del exc_info

    def render(self, context, funcname='__main__'):
        return self.render_to_buffer(context, funcname).join()


parsers = {
    'tonnikala':    parse_tonnikala,
    'js_tonnikala': parse_js_tonnikala,
    'chameleon':    parse_chameleon,
}


class TemplateInfo(object):
    def __init__(self, filename, lnotab):
        self.filename = filename
        self.lnotab = lnotab

    def get_corresponding_lineno(self, line):
        return self.lnotab.get(line, line)


def _new_globals(runtime):
    return {
        '__TK__runtime':      runtime,
        '__TK__mkbuffer':     runtime.Buffer,
        '__TK__escape':       runtime.escape,
        '__TK__output_attrs': runtime.output_attrs,
        'literal':            helpers.literal
    }


class Loader(object):
    handle_exception = staticmethod(handle_exception)
    runtime = python.TonnikalaRuntime

    def __init__(self, debug=False, syntax='tonnikala', translatable=False):
        self.debug = debug
        self.syntax = syntax
        self.translatable = translatable

    def load_string(self, string, filename="<string>"):
        parser_func = parsers.get(self.syntax)
        if not parser_func:
            raise ValueError("Invalid parser syntax %s: valid syntaxes: %r"
                             % sorted(parsers.keys()))

        try:
            tree = parser_func(filename, string, translatable=self.translatable)
            gen = PythonGenerator(tree)
            code = gen.generate_ast()
            exc_info = None
        except exceptions.TemplateSyntaxError as e:
            if e.source is None:
                e.source = string
            if e.filename is None:
                e.filename = filename

            exc_info = sys.exc_info()

        if exc_info:
            self.handle_exception(exc_info, string, tb_override=None)

        if self.debug:
            import ast

            print(ast.dump(code, True, True))

            try:
                import astor
                print(astor.codegen.to_source(code))
            except ImportError:
                print("Not reversing AST to source as astor was not installed")

        runtime = self.runtime()
        runtime.loader = self
        glob = _new_globals(runtime)

        compiled = compile(code, filename, 'exec')
        glob['__TK_template_info__'] = TemplateInfo(filename, gen.lnotab_info())

        exec(compiled, glob, glob)

        template_func = glob['__TK__binder']
        return Template(template_func)


class FileLoader(Loader):
    def __init__(self, paths=[], debug=False, syntax='tonnikala', *args, **kwargs):
        super(FileLoader, self).__init__(*args, debug=debug, syntax=syntax, **kwargs)

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
            raise OSError(errno.ENOENT, "File not found: %s" % name)

        with codecs.open(path, 'r', encoding='UTF-8') as f:
            contents = f.read()
            mtime = os.fstat(f.fileno()).st_mtime

        template = self.load_string(contents, filename=path)
        template.mtime = mtime
        template.path = path

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
