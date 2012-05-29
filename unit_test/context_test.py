from cStringIO import StringIO
import unittest

from gitcvs import context, log

class TestLoggingShell(unittest.TestCase):
    def setUp(self):
        appConfig = StringIO('[global]\nlogdir = /logs\n'
                             '[export]\ncvsdir = /cvs')
        repConfig = StringIO('[dir/repo]\ncvspath = cvsprefix/rEpo')
        self.ctx = context.Context(appConfig, repConfig)

    def test_Internal(self):
        self.assertTrue(isinstance(self.ctx.logs, log.LogCache))

    def test_AppConfig(self):
        self.assertEqual(self.ctx.getLogDir(), '/logs')

    def test_RepoConfig(self):
        self.assertEqual(self.ctx.getRepositories(), set(('dir/repo',)))

    def test_AttributeError(self):
        def raiseAttributeError():
            self.ctx.doesNotExist()
        self.assertRaises(AttributeError, raiseAttributeError)

    def test_getCVSBranchCheckoutDir(self):
        branchdir = self.ctx.getCVSBranchCheckoutDir('dir/repo', 'a1')
        self.assertEqual(branchdir, '/cvs/repo/a1/rEpo')
