import mock
import os
from StringIO import StringIO
import tempfile
import testutils

from gitcvs import gitexport, context

class GitExportTest(testutils.TestCase):
    def setUp(self):
        self.username = 'janedoe'
        with mock.patch('gitcvs.log.Log') as mocklog:
            with mock.patch('gitcvs.log.LogCache') as mocklogcache:
                appConfig = StringIO('[global]\n'
                                     'logdir = /logdir\n'
                                     'gitdir = /gitdir\n'
                                     '[export]\n'
                                     'cvsdir = /cvsdir\n')
                repConfig = StringIO('[repo]\n'
                                     'gitroot = git@host\n'
                                     'cvsroot = asdf\n'
                                     'cvspath = Some/Loc\n'
                                     'git.master = b1\n'
                                     '[repo2]\n'
                                     'cvsroot = fdsa\n'
                                     'cvspath = Other/Loc\n'
                                     'git.b1 = b1\n'
                                     'git.master = b2\n'
                                     )
                self.ctx = context.Context(appConfig, repConfig)
                self.mocklog = mocklog()
                self.exp = gitexport.Exporter(self.ctx, self.username)
                self.Git = mock.Mock()
                self.CVS = mock.Mock()

    def tearDown(self):
        pass

    # tests exportBranches thoroughly
    def test_exportAll(self):
        with mock.patch.object(self.exp, 'exportgit'):
            self.exp.exportAll()
            self.exp.exportgit.assert_has_calls(
                [mock.call('repo', mock.ANY, mock.ANY, 'master', 'export-master'),
                 mock.call('repo2', mock.ANY, mock.ANY, 'b1', 'export-b1'),
                 mock.call('repo2', mock.ANY, mock.ANY, 'master', 'export-master')])

    def test_cloneGit(self):
        with mock.patch('os.chdir') as cd:
            with mock.patch('os.path.exists') as exists:
                exists.return_value = False
                self.exp.cloneGit(self.Git, 'repo', '/gitdir/repo')
                self.Git.clone.assert_called_once_with('git@host:repo')
                cd.assert_has_calls([mock.call('/gitdir'),
                                     mock.call('/gitdir/repo')])

    def test_cloneGitPopulated(self):
        with mock.patch('os.chdir') as cd:
            with mock.patch('os.path.exists') as exists:
                exists.return_value = True
                self.exp.cloneGit(self.Git, 'repo', '/gitdir/repo')
                self.Git.clone.assert_not_called()
                cd.assert_called_once_with('/gitdir/repo')

    def test_checkoutCVS(self):
        with mock.patch('os.makedirs') as md:
            with mock.patch('os.path.exists') as exists:
                exists.return_value = False
                self.CVS.path = '/cvsdir/repo/b1/Loc'
                self.exp.checkoutCVS(self.CVS)
                exists.assert_has_calls([
                    mock.call('/cvsdir/repo/b1'),
                    mock.call('/cvsdir/repo/b1/Loc')])
                md.assert_called_once_with('/cvsdir/repo/b1')
                self.CVS.checkout.assert_called_once_with()
                self.CVS.update.assert_not_called()

    def test_checkoutCVSPopulated(self):
        with mock.patch('os.makedirs') as md:
            with mock.patch('os.path.exists') as exists:
                exists.return_value = True
                self.CVS.path = '/cvsdir/repo/b1/Loc'
                self.exp.checkoutCVS(self.CVS)
                exists.assert_has_calls([
                    mock.call('/cvsdir/repo/b1'),
                    mock.call('/cvsdir/repo/b1/Loc')])
                md.assert_not_called()
                self.CVS.update.assert_called_once_with()
                self.CVS.checkout.assert_not_called()

    def test_prepareGitClone(self):
        with mock.patch('gitcvs.gitexport.Exporter.trackBranch') as tb:
            bi = ['b1', 'master']
            self.Git.branches.return_value = bi
            bo = self.exp.prepareGitClone(self.Git, 'b1', 'repo')
            self.assertEqual(bi, bo)
            self.Git.pristine.assert_called_once_with()
            tb.assert_called_once_with(self.Git, 'b1', bi, 'repo')
            self.Git.checkout.assert_called_once_with('b1')
            self.Git.mergeFastForward.assert_called_once_with('origin/b1')

    def test_calculateFileSetsEmpty(self):
        self.CVS.listContentFiles.return_value = []
        self.Git.listContentFiles.return_value = []
        G, D, AF, C, AD = self.exp.calculateFileSets(self.CVS, self.Git)
        self.assertEqual(G, set())
        self.assertEqual(D, set())
        self.assertEqual(AF, set())
        self.assertEqual(C, set())
        self.assertEqual(AD, set())

    def test_calculateFileSetsAlmostEmpty(self):
        self.CVS.listContentFiles.return_value = ['.cvsignore']
        self.Git.listContentFiles.return_value = []
        G, D, AF, C, AD = self.exp.calculateFileSets(self.CVS, self.Git)
        self.assertEqual(G, set())
        self.assertEqual(D, set())
        self.assertEqual(AF, set())
        self.assertEqual(C, set())
        self.assertEqual(AD, set())

    def test_calculateFileSetsNewDirectory(self):
        self.CVS.listContentFiles.return_value = ['/a/b', '/a/c']
        self.Git.listContentFiles.return_value = ['/a/b', '/a/c', '/b/a']
        G, D, AF, C, AD = self.exp.calculateFileSets(self.CVS, self.Git)
        self.assertEqual(G, set(('/a/b', '/a/c', '/b/a')))
        self.assertEqual(D, set())
        self.assertEqual(AF, set(('/b/a',)))
        self.assertEqual(C, set(('/a/b', '/a/c')))
        self.assertEqual(AD, set(('/b',)))

    def test_calculateFileSetsDeletedFiles(self):
        self.CVS.listContentFiles.return_value = ['/a/b', '/a/c']
        self.Git.listContentFiles.return_value = ['/a/b']
        G, D, AF, C, AD = self.exp.calculateFileSets(self.CVS, self.Git)
        self.assertEqual(G, set(('/a/b',)))
        self.assertEqual(D, set(('/a/c',)))
        self.assertEqual(AF, set())
        self.assertEqual(C, set(('/a/b',)))
        self.assertEqual(AD, set())

    def test_trackBranch(self):
        self.exp.trackBranch(self.Git, 'b1', set(('remotes/origin/b1',)),
                             'repo')
        self.Git.trackBranch.assert_called_once_with('b1')
        self.Git.newBranch.assert_not_called()

    def test_trackBranchNoCreate(self):
        self.assertRaises(KeyError,
            self.exp.trackBranch, self.Git, 'b1', set(()), 'repo')
        self.Git.trackBranch.assert_not_called()
        self.Git.newBranch.assert_not_called()

    # exportgit tested only by story testing
