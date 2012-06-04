from cStringIO import StringIO
import testutils

from gitcvs import context, log

class TestLoggingShell(testutils.TestCase):
    def setUp(self):
        appConfig = StringIO('[global]\nlogdir = /logs\n'
                             '[export]\ncvsdir = /cvs\n'
                             '[import]\ncvsdir = /cvsin\n'
                             )
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

    def test_getCVSExportDir(self):
        branchdir = self.ctx.getCVSExportDir('dir/repo')
        self.assertEqual(branchdir, '/cvsin/repo/rEpo')
