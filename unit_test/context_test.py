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
