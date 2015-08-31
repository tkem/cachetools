import unittest

import cachetools


class CacheKeysTest(unittest.TestCase):

    def test_hashkey(self, key=cachetools.hashkey):
        self.assertEqual(key(), key())
        self.assertEqual(hash(key()), hash(key()))
        self.assertEqual(key(1, 2, 3), key(1, 2, 3))
        self.assertEqual(hash(key(1, 2, 3)), hash(key(1, 2, 3)))
        self.assertEqual(key(1, 2, 3, x=0), key(1, 2, 3, x=0))
        self.assertEqual(hash(key(1, 2, 3, x=0)), hash(key(1, 2, 3, x=0)))
        self.assertNotEqual(key(1, 2, 3), key(3, 2, 1))
        self.assertNotEqual(key(1, 2, 3), key(1, 2, 3, x=None))
        self.assertNotEqual(key(1, 2, 3, x=0), key(1, 2, 3, x=None))
        self.assertNotEqual(key(1, 2, 3, x=0), key(1, 2, 3, y=0))
        with self.assertRaises(TypeError):
            hash(key({}))
        # untyped keys compare equal
        self.assertEqual(key(1, 2, 3), key(1.0, 2.0, 3.0))
        self.assertEqual(hash(key(1, 2, 3)), hash(key(1.0, 2.0, 3.0)))

    def test_typedkey(self, key=cachetools.typedkey):
        self.assertEqual(key(), key())
        self.assertEqual(hash(key()), hash(key()))
        self.assertEqual(key(1, 2, 3), key(1, 2, 3))
        self.assertEqual(hash(key(1, 2, 3)), hash(key(1, 2, 3)))
        self.assertEqual(key(1, 2, 3, x=0), key(1, 2, 3, x=0))
        self.assertEqual(hash(key(1, 2, 3, x=0)), hash(key(1, 2, 3, x=0)))
        self.assertNotEqual(key(1, 2, 3), key(3, 2, 1))
        self.assertNotEqual(key(1, 2, 3), key(1, 2, 3, x=None))
        self.assertNotEqual(key(1, 2, 3, x=0), key(1, 2, 3, x=None))
        self.assertNotEqual(key(1, 2, 3, x=0), key(1, 2, 3, y=0))
        with self.assertRaises(TypeError):
            hash(key({}))
        # typed keys compare unequal
        self.assertNotEqual(key(1, 2, 3), key(1.0, 2.0, 3.0))

    def test_addkeys(self, key=cachetools.hashkey):
        self.assertIsInstance(key(), tuple)
        self.assertIsInstance(key(1, 2, 3) + key(4, 5, 6), type(key()))
        self.assertIsInstance(key(1, 2, 3) + (4, 5, 6), type(key()))
        self.assertIsInstance((1, 2, 3) + key(4, 5, 6), type(key()))
