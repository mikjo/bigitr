#
# Copyright 2012 SAS Institute
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

from bigitr import cvsimport, context

class CVSImportTest(testutils.TestCase):
    def setUp(self):
        with mock.patch('bigitr.log.Log') as mocklog:
            with mock.patch('bigitr.log.LogCache') as mocklogcache:
                appConfig = StringIO('[global]\n'
                                     'logdir = /logdir\n'
                                     'gitdir = /gitdir\n'
                                     '[import]\n'
                                     'cvsdir = /cvsdir\n'
                                     '[export]\n'
                                     'cvsdir = /cvsdir\n')
                repConfig = StringIO('[GLOBAL]\n'
                                     'skeleton = /skel\n'
                                     '[repo]\n'
                                     'cvsroot = asdf\n'
                                     'cvspath = Some/Loc\n'
                                     'cvs.b1 = b1\n'
                                     'merge.cvs-b1 = b1\n'
                                     'merge.b1 = master\n'
                                     '[repo2]\n'
                                     'cvsroot = fdsa\n'
                                     'cvspath = Other/Loc\n'
                                     'cvs.b1 = b1\n'
                                     'cvs.b2 = b2\n'
                                     'merge.cvs-b1 = b1 b2\n'
                                     'merge.cvs-b2 = b2\n'
                                     )
                self.ctx = context.Context(appConfig, repConfig)
                self.mocklog = mocklog()
                self.imp = cvsimport.Importer(self.ctx)
                self.Git = mock.Mock()
                self.CVS = mock.Mock()

    # tests importBranches normal use thoroughly
    def test_importAll(self):
        with mock.patch.object(self.imp, 'importcvs'):
            self.imp.importAll()
            self.imp.importcvs.assert_has_calls(
                [mock.call('repo', mock.ANY, mock.ANY, 'b1', 'cvs-b1'),
                 mock.call('repo2', mock.ANY, mock.ANY, 'b1', 'cvs-b1'),
                 mock.call('repo2', mock.ANY, mock.ANY, 'b2', 'cvs-b2')])

    def test_importBranchesError(self):
        with mock.patch.object(self.imp, 'importcvs'):
            self.imp.importcvs.side_effect = lambda *x: 1/0
            self.assertRaises(ZeroDivisionError,
                self.imp.importBranches, 'repo', mock.Mock())

    @mock.patch('bigitr.ignore.Ignore.parse')
    @mock.patch('bigitr.gitmerge.Merger')
    @mock.patch('bigitr.util.copyFiles')
    @mock.patch('time.asctime')
    @mock.patch('os.remove')
    @mock.patch('bigitr.util.listFiles')
    @mock.patch('os.path.exists')
    @mock.patch('os.makedirs')
    @mock.patch('os.chdir')
    @mock.patch('os.rmdir')
    def test_importcvs(self, rmdir, cd, md, pe, lF, rm, at, cF, M, Ip):
        self.Git.branches.return_value = ['b1', 'master']
        self.Git.listContentFiles.return_value = ['a']
        at.return_value = 'TIME'
        self.imp.importcvs('repo2', self.Git, self.CVS, 'b1', 'cvs-b1')

        # spot test the most important things, but not everything
        self.Git.initializeGitRepository.assert_called()
        self.Git.checkoutNewImportBranch.assert_called_once_with('cvs-b1')
        self.Git.pristine.assert_called_once_with()
        cF.assert_has_calls([
            mock.call('/cvsdir/repo2/Loc', '/gitdir/repo2', mock.ANY),
            mock.call('/skel', '/gitdir/repo2', mock.ANY),
        ])
        self.assertEquals(cF.call_count, 2)
        self.Git.runImpPreHooks.assert_called_once_with('cvs-b1')
        self.Git.infoStatus.assert_called_once_with()
        self.Git.infoDiff.assert_called_once_with()
        self.Git.addAll.assert_called_once_with()
        self.Git.status.assert_has_calls([mock.call(), mock.call()])
        self.Git.commit.assert_called_once_with('import from CVS as of TIME')
        self.Git.push.assert_called_once_with('origin', 'cvs-b1', 'cvs-b1')
        self.Git.runImpPreHooks.assert_called_once_with('cvs-b1')
        M(self.ctx).mergeFrom.assert_called_once_with('repo2', self.Git, 'cvs-b1')

        self.Git.infoStatus.reset_mock()
        self.Git.commit.reset_mock()
        self.Git.status.side_effect = [True, False]
        self.imp.importcvs('repo2', self.Git, self.CVS, 'b1', 'cvs-b1')
        self.Git.infoStatus.assert_called_once_with()
        self.Git.commit.assert_not_called()

        self.Git.infoStatus.reset_mock()
        self.Git.commit.reset_mock()
        self.Git.status.side_effect = [False, True]
        self.imp.importcvs('repo2', self.Git, self.CVS, 'b1', 'cvs-b1')
        self.Git.infoStatus.assert_not_called()
        self.Git.commit.assert_called_once_with('import from CVS as of TIME')

        self.Git.status.side_effect = [False, False]
        self.Git.checkoutTracking.assert_not_called()
        self.Git.branches.return_value = ['remotes/origin/cvs-b1', 'b1', 'master']
        self.imp.importcvs('repo2', self.Git, self.CVS, 'b1', 'cvs-b1')
        self.Git.checkoutTracking.assert_called_once_with('cvs-b1')

        self.Git.status.side_effect = [False, False]
        self.Git.checkoutTracking.reset_mock()
        self.Git.fetch.reset_mock()
        self.Git.mergeFastForward.reset_mock()
        self.Git.branches.return_value = ['remotes/origin/cvs-b1', 'cvs-b1', 'b1', 'master']
        self.Git.branch.return_value = 'master'
        self.imp.importcvs('repo2', self.Git, self.CVS, 'b1', 'cvs-b1')
        self.Git.checkout.assert_called_once_with('cvs-b1')
        self.Git.fetch.assert_called_once_with()
        self.Git.mergeFastForward.assert_called_once_with('origin/cvs-b1')

        self.Git.status.side_effect = [False, False]
        self.Git.fetch.reset_mock()
        self.Git.mergeFastForward.reset_mock()
        self.Git.branch.return_value = 'cvs-b1'
        self.imp.importcvs('repo2', self.Git, self.CVS, 'b1', 'cvs-b1')
        self.Git.checkout.assert_not_called()
        self.Git.fetch.assert_called_once_with()
        self.Git.mergeFastForward.assert_called_once_with('origin/cvs-b1')

        lF.return_value = []
        self.assertRaises(RuntimeError,
            self.imp.importcvs, 'repo2', self.Git, self.CVS, 'b1', 'cvs-b1')
