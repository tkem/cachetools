import unittest

import cachetools

from . import CacheTestMixin


class CacheTest(unittest.TestCase, CacheTestMixin):
    Cache = cachetools.Cache
    
    def test_on_evict_callback(self):
        # Test that the on_evict callback is called when items are evicted
        evicted_items = {}
        
        def on_evict(key, value):
            evicted_items[key] = value
        
        # Use LRUCache instead of base Cache to ensure proper item eviction
        cache = cachetools.LRUCache(2, on_evict=on_evict)
        
        # Fill the cache
        cache[1] = 'one'
        cache[2] = 'two'
        
        # This should evict key 1
        cache[3] = 'three'
        
        # Check that the callback was called with the correct key and value
        self.assertEqual(evicted_items, {1: 'one'})
        
        # Add another item to evict key 2
        cache[4] = 'four'
        
        # Check that the callback was called again
        self.assertEqual(evicted_items, {1: 'one', 2: 'two'})
    
    def test_on_evict_exception(self):
        # Test that exceptions in the on_evict callback are caught
        
        def on_evict_error(key, value):
            raise ValueError("Test exception")
        
        # Use LRUCache instead of base Cache to ensure proper item eviction
        cache = cachetools.LRUCache(2, on_evict=on_evict_error)
        
        # Fill the cache
        cache[1] = 'one'
        cache[2] = 'two'
        
        # This should evict key 1 and call the callback which raises an exception
        # The exception should be caught and not propagate
        try:
            cache[3] = 'three'
        except ValueError:
            self.fail("Exception from on_evict callback was not caught")
        
        # Verify the item was still added despite the callback exception
        self.assertEqual(cache[3], 'three')
