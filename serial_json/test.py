#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals

import json
import sys
import unittest

import serial_json

try:
    from cStringIO import StringIO
except ImportError:
    try:
        from StringIO import StringIO
    except ImportError:
        from io import StringIO

class TestParsing(unittest.TestCase):
    def check(self, value):
        self.assertEqual(next(serial_json.loads(value))[1], json.loads(value))

    def test_primitives(self):
        for value in 'true false null'.split():
            self.check(value)

    def test_numbers(self):
        for value in '1234 1.23 1e43 -1.2e43'.split():
            self.check(value)

    def test_arrays(self):
        result = list(serial_json.loads('[1, 2, [3, 4], 5]'))
        self.assertEqual(result, [
            ('$[0]', 1.0),
            ('$[1]', 2.0),
            ('$[2][0]', 3.0),
            ('$[2][1]', 4.0),
            ('$[3]', 5.0)
        ])

    def test_objects(self):
        result = list(serial_json.loads('{"foo": 3, "bar": [{"baz": 4}]}'))
        self.assertEqual(result, [
            ('$.foo', 3.0),
            ('$.bar[0].baz', 4.0)
        ])

    def test_string(self):
        for value in ('""', '" "', '"abc def"'):
            self.check(value)

    def test_escaped_strings(self):
        for value in ('"\\n"', '"\\""', '"\\\\"'):
            self.check(value)

    def test_escaped_unicode(self):
        self.check('"\\u04d2"')

    def test_raw_unicode(self):
        self.check(u'"あ"')

    def test_illegal_strings(self):
        try:
            val = next(serial_json.loads('"\\"'))
        except:
            pass
        else:
            self.fail("Failed to throw exception: " + str(val))

    def test_rewind(self):
        buf = StringIO('{"foo": 3, "bar": [{"baz": 4}]}')
        p = serial_json.load(buf)
        a1 = list(p)
        p.reset()
        a2 = list(p)
        assert a1 == a2

    def test_buffer_size(self):
        for i in range(2, 6):
            buf = StringIO(
                '{"really_long_key": "really_long_value"}')
            list(serial_json.load(buf, buffer_size=i))

if __name__ == '__main__':
    unittest.main()
