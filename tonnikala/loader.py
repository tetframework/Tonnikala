from tonnikala import expr
from tonnikala.languages import javascript
from tonnikala import parser
from os import path
from tonnikala.ir.generate import IRGenerator
from tonnikala.languages.python.generator import Generator as PythonGenerator
from tonnikala.languages.javascript.generator import Generator as JavascriptGenerator
from tonnikala.runtime import python
from tonnikala.parser import Parser
import six

if six.PY3:
    import builtins as __builtin__
else:
    import __builtin__

class Helpers():
    pass

helpers = Helpers()
helpers.literal = lambda x: x

class BuiltIn(object):
    def __init__(self, chain=[helpers]):
        self.builtins = {}
        for i in [ __builtin__ ] + list(reversed(chain)):
            for j in dir(i):
                if not j.startswith('__') and not j.endswith('__'):
                    self.builtins[j] = getattr(i, j)

    def __getitem__(self, key):
        return self.builtins[key]

    def __contains__(self, key):
        return key in self.builtins

NOT_FOUND = object()

class TemplateContext(object):
    def __init__(self, context, builtins=BuiltIn()):
        self.context = dict(context)
        self.builtins = builtins

    def __getitem__(self, key):
        try:
            return self.context[key]

        except KeyError as e:
            self.context[key] = rv = self.builtins[key]
            return rv

    def __contains__(self, key):
        try:
            return self[key] is not NOT_FOUND

        except KeyError:
            self.context[key] = NOT_FOUND
            return False

class Template(object):
    def __init__(self, binder, importer):
        self.func = binder
        self.importer = importer

    def render(self, context, function='__main__'):
        return getattr(self.func(TemplateContext(context)), function)()


class Loader(object):
    def __init__(self, debug=False):
        self.debug = debug

    def load_string(self, string, filename="<string>", import_loader=None):
        parser = Parser(filename, string)
        parsed = parser.parse()
        generator = IRGenerator(parsed)
        tree = generator.generate_tree()

        if self.debug:
            print(tree)

        tree = generator.flatten_element_nodes(tree)
        tree = generator.merge_text_nodes(tree)
        code = PythonGenerator(tree).generate_ast()

        if self.debug:
            import ast
            import astor

            print(ast.dump(code))
            print(astor.codegen.to_source(code))

        # import astor
        # print(astor.codegen.to_source(code))

        glob = {
            '__tonnikala__': python,
            'literal':       lambda x: x
        }

        compiled = compile(code, '<string>', 'exec')
        exec(compiled, glob, glob)
        template_func = glob['__tk__binder__']
        return Template(template_func, ImportLoader(self))


class ImportLoader(object):
    def __init__(self, loader):
        self.loaded = {}

    def load_template(self, file):
        pass


def load_template():
    pass



