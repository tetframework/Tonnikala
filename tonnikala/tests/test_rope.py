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
        self.assertEquals(unicode(rope), u'abc')

    def test_rope_empty(self):
        rope = Rope()
        self.assertEquals(unicode(rope), '')

    def test_rope_string(self):
        rope = Rope()
        self.assertRaises(TypeError, rope.append, (b'123',))

    def test_rope_appends(self):
        rope = Rope()
        rope.append(u'a')
        rope.append(u'bb')
        rope.append(u'ccc')

        combined = Rope()
        combined.append(u'1')
        combined.append(rope)
        combined.append(rope)
        combined.append(rope)
        combined.append(u'2')

        self.assertEquals(unicode(combined), u'1abbcccabbcccabbccc2')
