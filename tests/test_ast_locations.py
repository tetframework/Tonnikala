"""
Regression tests for generated AST end locations.

CPython 3.11+ validates the AST passed to compile() and rejects any node
whose end_lineno/end_col_offset precede its lineno/col_offset. Nodes
remapped by LocationMapper and the synthesised block-call nodes used to
keep stale end locations, so templates with a py:block nested inside
another block on a later line (the typical layout for inherited templates)
failed with e.g. ``ValueError: AST node line range (98, 97) is not valid``.
The fix is ``normalize_end_locations`` in ``Generator.generate_ast``.
"""

import ast
import os.path
import unittest

from tonnikala.languages.python.generator import Generator
from tonnikala.loader import FileLoader, Loader
from tonnikala.syntaxes.tonnikala import parse

data_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "files")

NESTED_BLOCK_TEMPLATE = """\
<html>
<py:block name="outer">
<h1>${title}</h1>


<py:block name="inner">inner ${title}</py:block>
</py:block>
</html>"""

NESTED_BLOCK_OUTPUT = """\
<html>

<h1>x</h1>


inner x

</html>"""


def read_file(*path):
    with open(os.path.join(data_dir, *path), "r", encoding="UTF-8", newline="") as f:
        return f.read()


def generate_ast(source):
    return Generator(parse("<string>", source)).generate_ast()


def invalid_locations(tree):
    """
    Return a description of every node whose end location precedes its
    start location; the same check CPython 3.11+ does in compile().
    """
    errors = []
    for node in ast.walk(tree):
        lineno = getattr(node, "lineno", None)
        end_lineno = getattr(node, "end_lineno", None)
        if lineno is None or end_lineno is None:
            continue

        start = (lineno, getattr(node, "col_offset", 0))
        end = (end_lineno, getattr(node, "end_col_offset", None))
        if end[1] is None:
            end = (end[0], start[1])

        if end < start:
            errors.append("%s: start %r, end %r" % (type(node).__name__, start, end))

    return errors


class TestAstEndLocations(unittest.TestCase):
    def assert_valid_locations(self, source):
        errors = invalid_locations(generate_ast(source))
        self.assertEqual(errors, [], "generated AST has invalid end locations")

    def test_nested_block_ast_locations_valid(self):
        # Checks the AST directly, so this fails on every Python version,
        # not only on those where compile() validates locations.
        self.assert_valid_locations(NESTED_BLOCK_TEMPLATE)

    def test_file_templates_ast_locations_valid(self):
        for name in sorted(os.listdir(os.path.join(data_dir, "input"))):
            with self.subTest(template=name):
                self.assert_valid_locations(read_file("input", name))

    def test_nested_block_compiles_and_renders(self):
        template = Loader().load_string(NESTED_BLOCK_TEMPLATE)
        self.assertEqual(str(template.render({"title": "x"})), NESTED_BLOCK_OUTPUT)

    def test_inherited_template_with_nested_block(self):
        loader = FileLoader()
        loader.add_path(os.path.join(data_dir, "input"))
        for name, title in [
            ("nested_base.tk", "the base"),
            ("nested_child.tk", "the child"),
        ]:
            with self.subTest(template=name):
                output = loader.load(name).render({"title": title})
                self.assertEqual(str(output), read_file("output", name).rstrip("\n"))
