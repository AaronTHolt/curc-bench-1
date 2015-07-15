import bench.driver
import mock
import os
import re
import unittest

class TestDriver(unittest.TestCase):
    def setUp(self):
        self.parser = driver.parser()

    def test_parser(self):
        parsed = self.parser.parse_args(['--verbose', '--directory', 
                            'fake_dir'])
        self.assertEqual(parsed.directory, 'fake_dir')