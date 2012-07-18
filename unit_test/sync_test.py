import mock
import os
from StringIO import StringIO
import tempfile
import testutils

from gitcvs import sync, context, git

class TestSync(testutils.TestCase):
    def setUp(self):
        with mock.patch('gitcvs.log.Log') as mocklog:
            with mock.patch('gitcvs.log.LogCache') as mocklogcache:
                appConfig = StringIO('[global]\n'
                                     'logdir = /logdir\n'
                                     'gitdir = /gitdir\n'
                                     '[import]\n'
                                     '[export]\n'
                                     'cvsdir = /cvsdir\n')
                repConfig = StringIO('[repo]\n'
                                     '[repo2]\n'
                                     )
                self.ctx = context.Context(appConfig, repConfig)
                self.mocklog = mocklog()
                self.sync = sync.Synchronizer(self.ctx)
                self.sync.imp = mock.Mock()
                self.sync.exp = mock.Mock()
                self.sync.err = mock.Mock()

    def test_synchronize(self):
        Git = git.Git(self.ctx, 'repo')
        self.sync.synchronize('repo', Git)
        self.sync.imp.importBranches.assert_has_calls([
            mock.call('repo', Git),
            mock.call('repo', Git)])
        self.sync.exp.exportBranches.assert_called_once_with('repo', Git)

    def test_synchronizeNoPreImport(self):
        Git = git.Git(self.ctx, 'repo')
        self.ctx.getExportPreImport = mock.Mock()
        self.ctx.getExportPreImport.return_value = False
        self.sync.synchronize('repo', Git)
        self.ctx.getExportPreImport.assert_called_once_with()
        self.sync.imp.importBranches.assert_called_once_with('repo', Git)
        self.sync.exp.exportBranches.assert_called_once_with('repo', Git)

    def test_synchronizeAll(self):
        self.sync.synchronizeAll()
        self.sync.imp.importBranches.assert_has_calls([
            mock.call('repo', mock.ANY),
            mock.call('repo', mock.ANY),
            mock.call('repo2', mock.ANY),
            mock.call('repo2', mock.ANY)])
        self.sync.exp.exportBranches.assert_has_calls([
            mock.call('repo', mock.ANY),
            mock.call('repo2', mock.ANY)])
        self.sync.err.assert_no_calls()

    def test_synchronizeAllWithError(self):
        def raiseAnError(repo, Git):
            if repo == 'repo':
                1/0

        self.sync.exp.exportBranches.side_effect = raiseAnError
        self.sync.synchronizeAll()
        self.sync.err.report.assert_called_once_with('repo')
        self.sync.imp.importBranches.assert_has_calls([
            mock.call('repo', mock.ANY),
            # NOT second mock.call('repo', mock.ANY),
            mock.call('repo2', mock.ANY),
            mock.call('repo2', mock.ANY)])
        self.sync.exp.exportBranches.assert_has_calls([
            mock.call('repo', mock.ANY),
            mock.call('repo2', mock.ANY)])
