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

from bigitr import appconfig
from bigitr import context
from bigitr import log
from bigitr import repositorymap

class TestLoggingShell(testutils.TestCase):
    def setUp(self):
        self.appConfig = StringIO('[global]\nlogdir = /logs\n'
                                 '[export]\ncvsdir = /cvs\n'
                                 '[import]\ncvsdir = /cvsin\n'
                                 )
        self.repConfig = StringIO('[dir/repo]\ncvspath = cvsprefix/rEpo')
        self.ctx = context.Context(self.appConfig, self.repConfig)

    def assertContextObjectsNotString(self):
        self.assertTrue(isinstance(self.ctx._ac, appconfig.AppConfig))
        self.assertTrue(isinstance(self.ctx._rm, repositorymap.RepositoryConfig))

    def test_initTakesStringOrObjects(self):
        # strings resolved to objects in setUp
        self.assertContextObjectsNotString()
        # now pass in objects
        appCfg = appconfig.AppConfig(self.appConfig)
        repCfg = repositorymap.RepositoryConfig(self.repConfig)
        self.ctx = context.Context(appCfg, repCfg)
        self.assertContextObjectsNotString()

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
