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

from gitcvs import gitmerge, context

class GitMergeTest(testutils.TestCase):
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
                self.mrg = gitmerge.Merger(self.ctx)


    def test_merge(self):
        Git = mock.Mock()
        Git.mergeDefault.return_value = 0
        rc = self.mrg.merge('repo2', Git, 'cvs-b1')
        Git.checkout.assert_has_calls([mock.call('b1'), mock.call('b2')])
        Git.mergeFastForward.assert_has_calls(
            [mock.call('origin/b1'), mock.call('origin/b2')])
        Git.mergeDefault.assert_has_calls(
            [mock.call('cvs-b1', "Automated merge 'cvs-b1' into 'b1'"),
             mock.call('cvs-b1', "Automated merge 'cvs-b1' into 'b2'")])
        Git.push.assert_has_calls(
            [mock.call('origin', 'b1', 'b1'),
             mock.call('origin', 'b2', 'b2')]
        )
        self.assertTrue(rc)
        Git.reset_mock()
        rc = self.mrg.merge('repo2', Git, 'cvs-b2')
        Git.checkout.assert_called_once_with('b2')
        Git.mergeDefault.assert_called_once_with(
            'cvs-b2', "Automated merge 'cvs-b2' into 'b2'")
        Git.push.assert_called_once_with('origin', 'b2', 'b2')
        self.assertTrue(rc)

    def test_mergeFailure(self):
        Git = mock.Mock()
        Git.mergeDefault.return_value = 1
        rc = self.mrg.merge('repo2', Git, 'cvs-b1')
        Git.checkout.assert_has_calls([mock.call('b1'), mock.call('b2')])
        self.assertFalse(rc)

    def test_mergeCascade(self):
        Git = mock.Mock()
        Git.mergeDefault.return_value = 0
        rc = self.mrg.merge('repo', Git, 'cvs-b1')
        Git.checkout.assert_has_calls([mock.call('b1'), mock.call('master')])
        self.assertTrue(rc)

    def test_mergeFailureNoCascade(self):
        Git = mock.Mock()
        Git.mergeDefault.return_value = 1
        rc = self.mrg.merge('repo', Git, 'cvs-b1')
        Git.checkout.assert_called_once_with('b1') # not 'master'
        self.assertFalse(rc)

    def test_mergeFailureInCascade(self):
        Git = mock.Mock()
        Git.mergeDefault.return_value = 0
        Git.mergeDefault.side_effect = lambda x, y: x == 'b1'
        rc = self.mrg.merge('repo', Git, 'cvs-b1')
        Git.checkout.assert_has_calls([mock.call('b1'), mock.call('master')])
        Git.push.assert_called_once_with('origin', 'b1', 'b1') # not 'master'
        self.assertFalse(rc)

    def test_mergeBranches(self):
        Git = mock.Mock()
        with mock.patch('gitcvs.gitmerge.Merger.mergeBranch') as mb:
            self.mrg.mergeBranches('repo2', Git)
            mb.assert_has_calls(
                [mock.call('repo2', mock.ANY, 'cvs-b2'),
                 mock.call('repo2', mock.ANY, 'cvs-b1')])

    def test_mergeBranchesError(self):
        Git = mock.Mock()
        def raiseError():
            raise RuntimeError

        with mock.patch('gitcvs.gitmerge.Merger.mergeBranch') as mb:
            mb.side_effect = lambda x, y, z: raiseError()
            self.assertRaises(RuntimeError, self.mrg.mergeBranches, 'repo2', Git)
            mb.assert_called_once_with('repo2', mock.ANY, 'cvs-b2')

    def test_mergeBranch(self):
        Git = mock.Mock()
        with mock.patch('gitcvs.gitmerge.Merger.mergeFrom') as mf:
            self.mrg.mergeBranch('repo', Git, 'cvs-b1')
            Git.initializeGitRepository.assert_called_once_with(create=False)
            mf.assert_called_once_with('repo', Git, 'cvs-b1')

    def test_mergeFrom(self):
        Git = mock.Mock()
        with mock.patch('gitcvs.gitmerge.Merger.merge') as m:
            self.mrg.mergeFrom('repo2', Git, 'cvs-b1')
            self.Git.pristine.assert_called_once_with()
            m.assert_called_once_with('repo2', Git, 'cvs-b1')

    def test_mergeFrom(self):
        Git = mock.Mock()
        with mock.patch('gitcvs.gitmerge.Merger.merge') as m:
            m.return_value = False
            self.assertRaises(RuntimeError, self.mrg.mergeFrom, 'repo2', Git, 'cvs-b1')
            Git.pristine.assert_called_once_with()
            m.assert_called_once_with('repo2', Git, 'cvs-b1')
