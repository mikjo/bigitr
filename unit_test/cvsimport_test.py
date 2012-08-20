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

from gitcvs import cvsimport, context

class CVSImportTest(testutils.TestCase):
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
                self.imp = cvsimport.Importer(self.ctx)

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

    # importcvs tested only by story testing
