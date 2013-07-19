from __future__ import absolute_import, division, print_function, unicode_literals

import unittest
import six

from tonnikala._rope import Rope

class TestRope(unittest.TestCase):
    def test_rope_simple(self):
        rope = Rope()
        rope.append(u'a')
        rope.append(u'b')
        rope.append(u'c')
        print("appends done")
        self.assertEquals(unicode(rope), u'abc')
