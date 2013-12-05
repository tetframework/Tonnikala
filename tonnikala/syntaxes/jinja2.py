# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__docformat__ = "epytext"

"""XML parser"""

import six
from six import text_type

from tonnikala.ir.nodes import Element, Text, If, For, Define, Import, \
    EscapedText, MutableAttribute, ContainerNode, EscapedText, Root,   \
    DynamicAttributes, Unless, Expression, Comment

from tonnikala.expr     import handle_text_node # TODO: move this elsewhere.
from tonnikala.ir.tree  import IRTree
from tonnikala.ir.generate import BaseIRGenerator

def tokenize_jinja2(contents):
    yield TOKENS


class Jinja2IRGenerator(BaseIRGenerator):
    def __init__(self, content, *a, **kw):
        super(Jinja2IRGenerator, self).__init__(*a, **kw)

        self.tokenizer = tokenize_jinja2(contents)
        self.tree = IRTree()
        self.element_stack = []


    def generate_tree(self):
        current = Root()
        self.tree.add_child(current)

        for type, value in self.tokenizer:
            pass

        return self.tree

def parse(filename, contents):
    generator = Jinja2IRGenerator(parsed)

    tree = generator.generate_tree()
    tree = generator.merge_text_nodes(tree)

    return tree
