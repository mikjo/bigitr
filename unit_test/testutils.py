import os
import unittest

from gitcvs import util

class TestCase(unittest.TestCase):
    @staticmethod
    def removeRecursive(dir):
        util.removeRecursive(dir)
