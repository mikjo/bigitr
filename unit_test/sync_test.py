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

from bigitr import sync, context, git, shell

class TestSync(testutils.TestCase):
    def setUp(self):
        with mock.patch('bigitr.log.Log') as mocklog:
            with mock.patch('bigitr.log.LogCache') as mocklogcache:
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

    def test_synchronizeAllWithPythonError(self):
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
        self.ctx.logs['repo'].mailLastOutput.assert_not_called()

    def test_synchronizeAllWithCommandError(self):
        def raiseAnError(repo, Git):
            if repo == 'repo':
                raise shell.ErrorExitCode(1)

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
        self.ctx.logs['repo'].mailLastOutput.assert_called_once_with(mock.ANY)
