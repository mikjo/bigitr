#
# Copyright 2012-2013 SAS Institute
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import mock
import os
from StringIO import StringIO
import tempfile
import testutils

from bigitr import gitexport, context, shell, util

class GitExportTest(testutils.TestCase):
    def setUp(self):
        with mock.patch('bigitr.log.Log') as mocklog:
            with mock.patch('bigitr.log.LogCache') as mocklogcache:
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
                self.exp = gitexport.Exporter(self.ctx)
                self.Git = mock.Mock()
                self.CVS = mock.Mock()
                self.CVS.path = '/gitdir'

    def tearDown(self):
        pass

    # tests exportBranches normal use thoroughly
    def test_exportAll(self):
        with mock.patch.object(self.exp, 'exportgit'):
            self.exp.exportAll()
            self.exp.exportgit.assert_has_calls(
                [mock.call('repo', mock.ANY, mock.ANY, 'master', 'export-master'),
                 mock.call('repo2', mock.ANY, mock.ANY, 'b1', 'export-b1'),
                 mock.call('repo2', mock.ANY, mock.ANY, 'master', 'export-master')])

    def test_exportBranchesError(self):
        with mock.patch.object(self.exp, 'exportgit'):
            self.exp.exportgit.side_effect = lambda *x: 1/0
            self.assertRaises(ZeroDivisionError,
                self.exp.exportBranches, 'repo', self.Git)

    @mock.patch('bigitr.gitexport.Exporter.assertNoCVSMetaData')
    @mock.patch('bigitr.gitexport.Exporter.calculateFileSets')
    @mock.patch('bigitr.gitexport.Exporter.checkoutCVS')
    @mock.patch('bigitr.gitexport.Exporter.getGitMessages')
    @mock.patch('bigitr.gitexport.Exporter.prepareGitClone')
    @mock.patch('bigitr.gitexport.Exporter.cloneGit')
    @mock.patch('os.chdir')
    def test_exportgit(self, cd, cG, pGC, gGM, cC, cFS, aNCMD):
        pGC.return_value = set(('b1', 'export-b1', 'remotes/origin/export-b1'))
        gGM.return_value = 'message'
        cFS.return_value = [set(('f',)), set(), set(('f',)), set(), set(), set()]
        self.CVS.branch = 'b1'
        self.exp.exportgit('repo2', self.Git, self.CVS, 'b1', 'export-b1')
        cG.assert_called_with('repo2', self.Git, '/'.join((self.ctx.getGitDir(), 'repo2')))
        pGC.assert_called_with('repo2', self.Git, 'b1')
        gGM.assert_called_with(self.Git, pGC.return_value,
                               set(('export-b1', 'remotes/origin/export-b1')),
                               'b1', 'remotes/origin/export-b1')
        self.Git.runExpPreHooks.assert_called_with('b1')
        cC.assert_called_with(self.CVS)
        cFS.assert_called_with(self.CVS, self.Git)
        aNCMD.assert_called_with(set(()))
        self.CVS.deleteFiles.assert_called_with([])
        self.CVS.copyFiles.assert_called_with('/gitdir/repo2', ['f'])
        self.CVS.addDirectories.assert_called_with([])
        self.CVS.addFiles.assert_called_with(['f'])
        self.CVS.runPreHooks.assert_called_with()
        self.Git.infoDiff.assert_called_with('remotes/origin/export-b1', 'b1')
        self.CVS.commit.assert_called_with('message')
        self.Git.push.assert_called_with('origin', 'b1', 'export-b1')
        self.CVS.runPostHooks.assert_called_with()
        self.Git.runExpPostHooks.assert_called_with('b1')

        # test other cases from the bottom up
        self.Git.infoDiff.reset_mock()
        pGC.return_value = set(('b1',))
        self.exp.exportgit('repo2', self.Git, self.CVS, 'b1', 'export-b1')
        self.Git.infoDiff.assert_not_called()

        self.ctx._rm.set('repo2', 'prefix.b1', 'pre')
        self.exp.exportgit('repo2', self.Git, self.CVS, 'b1', 'export-b1')
        self.CVS.commit.assert_called_with('pre\n\nmessage')

        cFS.return_value = [set(('f',)), set(('a',)), set(('f',)), set(), set(), set(('a',))]
        self.assertRaises(RuntimeError,
            self.exp.exportgit, 'repo2', self.Git, self.CVS, 'b1', 'export-b1')

        cFS.return_value = [set(('a', 'f',)), set(), set(('a',)), set(), set(('a',)), set()]
        self.assertRaises(RuntimeError,
            self.exp.exportgit, 'repo2', self.Git, self.CVS, 'b1', 'export-b1')

        cFS.return_value = [set(), set(), set(), set(), set(), set()]
        self.assertRaises(RuntimeError,
            self.exp.exportgit, 'repo2', self.Git, self.CVS, 'b1', 'export-b1')

        gGM.return_value = ''
        self.Git.runExpPreHooks.reset_mock()
        self.exp.exportgit('repo2', self.Git, self.CVS, 'b1', 'export-b1')
        # ensure that it returned before the very next statement
        self.Git.runExpPreHooks.assert_not_called()

    def test_getGitMessages(self):
        gm = self.exp.getGitMessages(self.Git,
            set(['a',]),
            set(['e-a', 'remotes/origin/e-a']),
            'a',  'remotes/origin/e-a')
        self.assertEqual(gm, 'Initial export to CVS from git branch a')
        self.Git.logmessages.assert_not_called()

        self.Git.logmessages.return_value = 'fakemessage'
        gm = self.exp.getGitMessages(self.Git,
            set(['a', 'e-a', 'remotes/origin/e-a']),
            set(['e-a', 'remotes/origin/e-a']),
            'a',  'remotes/origin/e-a')
        self.assertEqual(gm, 'fakemessage')

    def test_assertNoCVSMetaData(self):
        self.exp.assertNoCVSMetaData(['a', 'b'])
        self.exp.assertNoCVSMetaData(['CVSa', 'bCVS'])
        self.assertRaises(RuntimeError, self.exp.assertNoCVSMetaData,
            ['a', 'CVS'])
        self.assertRaises(RuntimeError, self.exp.assertNoCVSMetaData,
            ['a', 'a/CVS'])

    def test_cloneGit(self):
        with mock.patch('os.chdir') as cd:
            with mock.patch('os.path.exists') as exists:
                exists.return_value = False
                self.exp.cloneGit('repo', self.Git, '/gitdir/repo')
                self.Git.clone.assert_called_once_with('git@host:repo')
                cd.assert_has_calls([mock.call('/gitdir'),
                                     mock.call('/gitdir/repo')])

    def test_cloneGitPopulated(self):
        with mock.patch('os.chdir') as cd:
            with mock.patch('os.path.exists') as exists:
                exists.return_value = True
                self.exp.cloneGit('repo', self.Git, '/gitdir/repo')
                self.Git.clone.assert_not_called()
                cd.assert_called_once_with('/gitdir/repo')

    def test_checkoutCVS(self):
        with mock.patch('os.makedirs') as md:
            with mock.patch('os.path.exists') as exists:
                exists.side_effect = [False, False, True]
                self.CVS.path = '/cvsdir/repo/b1/Loc'
                self.exp.checkoutCVS(self.CVS)
                exists.assert_has_calls([
                    mock.call('/cvsdir/repo/b1'),
                    mock.call('/cvsdir/repo/b1/Loc'),
                    mock.call('/cvsdir/repo/b1/Loc')])
                md.assert_called_once_with('/cvsdir/repo/b1')
                self.CVS.checkout.assert_called_once_with()
                self.CVS.update.assert_not_called()

    def test_checkoutCVSEmpty(self):
        'Raise a useful error if the directory does not exist'
        with mock.patch('os.makedirs') as md:
            with mock.patch('os.path.exists') as exists:
                exists.return_value = False
                self.CVS.path = '/cvsdir/repo/b1/Loc'
                self.assertRaises(RuntimeError, self.exp.checkoutCVS, self.CVS)
                exists.assert_has_calls([
                    mock.call('/cvsdir/repo/b1'),
                    mock.call('/cvsdir/repo/b1/Loc'),
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

    @mock.patch('bigitr.gitexport.Exporter.trackBranch')
    @mock.patch('bigitr.util.removeRecursive')
    @mock.patch('os.chdir')
    def test_prepareGitClone(self, cd, rR, tb):
        bi = ['b1', 'master']
        self.Git.branches.return_value = bi
        bo = self.exp.prepareGitClone('repo', self.Git, 'b1')
        self.assertEqual(bi, bo)
        self.Git.pristine.assert_called_once_with()
        tb.assert_called_once_with('repo', self.Git, 'b1', bi)
        self.Git.checkout.assert_called_once_with('b1')
        self.Git.reset.assert_called_once_with('origin/b1')
        util.removeRecursive.assert_not_called()
        os.chdir.assert_not_called()

    def test_calculateFileSetsEmpty(self):
        self.CVS.listContentFiles.return_value = []
        self.Git.listContentFiles.return_value = []
        G, D, AF, C, DD, AD = self.exp.calculateFileSets(self.CVS, self.Git)
        self.assertEqual(G, set())
        self.assertEqual(D, set())
        self.assertEqual(AF, set())
        self.assertEqual(C, set())
        self.assertEqual(DD, set())
        self.assertEqual(AD, set())

    def test_calculateFileSetsAlmostEmpty(self):
        self.CVS.listContentFiles.return_value = ['.cvsignore']
        self.Git.listContentFiles.return_value = []
        G, D, AF, C, DD, AD = self.exp.calculateFileSets(self.CVS, self.Git)
        self.assertEqual(G, set())
        self.assertEqual(D, set())
        self.assertEqual(AF, set())
        self.assertEqual(C, set())
        self.assertEqual(DD, set())
        self.assertEqual(AD, set())

    def test_calculateFileSetsNewDirectory(self):
        self.CVS.listContentFiles.return_value = ['a/b', 'a/c']
        self.Git.listContentFiles.return_value = ['a/b', 'a/c', 'b/a']
        G, D, AF, C, DD, AD = self.exp.calculateFileSets(self.CVS, self.Git)
        self.assertEqual(G, set(('a/b', 'a/c', 'b/a')))
        self.assertEqual(D, set())
        self.assertEqual(AF, set(('b/a',)))
        self.assertEqual(C, set(('a/b', 'a/c')))
        self.assertEqual(DD, set())
        self.assertEqual(AD, set(('b',)))

    def test_calculateFileSetsNewRootFile(self):
        'https://github.com/mikjo/bigitr/issues/1'
        self.CVS.listContentFiles.return_value = ['a/b', 'a/c']
        self.Git.listContentFiles.return_value = ['a/b', 'a/c', 'b']
        G, D, AF, C, DD, AD = self.exp.calculateFileSets(self.CVS, self.Git)
        self.assertEqual(G, set(('a/b', 'a/c', 'b')))
        self.assertEqual(D, set())
        self.assertEqual(AF, set(('b',)))
        self.assertEqual(C, set(('a/b', 'a/c')))
        self.assertEqual(DD, set())
        self.assertEqual(AD, set(()))

    def test_calculateFileSetsDeletedFiles(self):
        self.CVS.listContentFiles.return_value = ['a/b', 'a/c']
        self.Git.listContentFiles.return_value = ['a/b']
        G, D, AF, C, DD, AD = self.exp.calculateFileSets(self.CVS, self.Git)
        self.assertEqual(G, set(('a/b',)))
        self.assertEqual(D, set(('a/c',)))
        self.assertEqual(AF, set())
        self.assertEqual(C, set(('a/b',)))
        self.assertEqual(DD, set())
        self.assertEqual(AD, set())

    def test_calculateFileSetsFileToDirectory(self):
        self.CVS.listContentFiles.return_value = ['a']
        self.Git.listContentFiles.return_value = ['a/b']
        G, D, AF, C, DD, AD = self.exp.calculateFileSets(self.CVS, self.Git)
        self.assertEqual(G, set(('a/b',)))
        self.assertEqual(D, set(('a',)))
        self.assertEqual(AF, set(('a/b',)))
        self.assertEqual(C, set(()))
        self.assertEqual(DD, set())
        self.assertEqual(AD, set(('a',)))

    def test_calculateFileSetsDirectoryToFile(self):
        self.CVS.listContentFiles.return_value = ['a/b']
        self.Git.listContentFiles.return_value = ['a']
        G, D, AF, C, DD, AD = self.exp.calculateFileSets(self.CVS, self.Git)
        self.assertEqual(G, set(('a',)))
        self.assertEqual(D, set(('a/b',)))
        self.assertEqual(AF, set(('a',)))
        self.assertEqual(C, set(()))
        self.assertEqual(DD, set(('a',)))
        self.assertEqual(AD, set())

    @mock.patch('bigitr.ignore.Ignore')
    def test_calculateFileSetsSync(self, I):
        # as if .bigitrsync contains two lines:
        # syncme.*
        # deleteme.*
        self.CVS.listContentFiles.return_value = [
            '.bigitrsync',
            'ignoreme',
            'syncme',
            'deleteme',
        ]
        self.Git.listContentFiles.return_value = [
            '.bigitrsync',
            'syncme',
            'syncme2',
            'ignoreme2',
        ]
        I().include.side_effect = [
            set(['syncme', 'syncme2']), # "syncme.*" matches git
            set(['deleteme']), # "deleteme.*" matches CVS; not present in Git
        ]
        I().filter.side_effect = lambda x: x
        G, D, AF, C, DD, AD = self.exp.calculateFileSets(self.CVS, self.Git)
        self.assertEqual(G, set(['syncme', 'syncme2'])) # not ignoreme2
        self.assertEqual(D, set(['deleteme']))
        self.assertEqual(AF, set(['syncme2']))
        self.assertEqual(C, set(['syncme']))
        self.assertEqual(DD, set())
        self.assertEqual(AD, set())
        I().include.assert_has_calls([
            mock.call(set(['syncme2', 'ignoreme2', 'syncme'])),
            mock.call(set(['ignoreme', 'deleteme'])),
        ])


    def test_trackBranch(self):
        self.exp.trackBranch('repo', self.Git, 'b1', set(('remotes/origin/b1',)))
        self.Git.trackBranch.assert_called_once_with('b1')
        self.Git.newBranch.assert_not_called()

    def test_trackBranchNoCreate(self):
        self.assertRaises(KeyError,
            self.exp.trackBranch, 'repo', self.Git, 'b1', set(()))
        self.Git.trackBranch.assert_not_called()
        self.Git.newBranch.assert_not_called()
