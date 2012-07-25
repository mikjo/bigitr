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

import os
from cStringIO import StringIO
import tempfile
import testutils

from gitcvs import appconfig

class TestAppConfig(testutils.TestCase):
    def setUp(self):
        self.fd, self.cf = tempfile.mkstemp(suffix='.gitcvs')
        file(self.cf, 'r+').write('''
[global]
gitdir = /path/to/directory/holding/git/repositories
logdir = /path/to/log/directory
mailfrom = sendinguser@host
smarthost = smtp.smarthost.name
[import]
onerror = continue
cvsdir = /path/to/directory/for/cvs/exports
[export]
preimport = false
onerror = warn
cvsdir = /path/to/directory/for/cvs/checkouts/for/branch/imports
''')
        self.cfg = appconfig.AppConfig(self.cf)

        fd, self.defaults = tempfile.mkstemp(suffix='.gitcvs')
        os.close(fd)
        file(self.defaults, 'r+').write('''
[global]
gitdir = /path/to/directory/holding/git/repositories
logdir = /path/to/log/directory
[import]
[export]
preimport = true
cvsdir = /path/to/directory/for/cvs/checkouts/for/branch/imports
''')
        self.cfgdef = appconfig.AppConfig(self.defaults)


    def tearDown(self):
        os.close(self.fd)
        os.remove(self.cf)
        os.remove(self.defaults)

    def test_getGitDir(self):
        self.assertEqual(self.cfg.getGitDir(),
            '/path/to/directory/holding/git/repositories')

    def test_getLogDir(self):
        self.assertEqual(self.cfg.getLogDir(),
            '/path/to/log/directory')

    def test_getMailFrom(self):
        self.assertEqual(self.cfg.getMailFrom(),
            'sendinguser@host')

    def test_getSmartHost(self):
        self.assertEqual(self.cfg.getSmartHost(),
            'smtp.smarthost.name')

    def test_getImportError(self):
        self.assertEqual(self.cfg.getImportError(),
            appconfig.CONTINUE)

    def test_getImportErrorDefault(self):
        self.assertEqual(self.cfgdef.getImportError(),
            appconfig.ABORT)

    def test_getExportCVSDir(self):
        self.assertEqual(self.cfg.getExportCVSDir(),
            '/path/to/directory/for/cvs/exports')

    def test_getExportPreImportFalse(self):
        self.assertEqual(self.cfg.getExportPreImport(),
            False)

    def test_getExportPreImportTrue(self):
        self.assertEqual(self.cfgdef.getExportPreImport(),
            True)

    def test_getExportError(self):
        self.assertEqual(self.cfg.getExportError(),
            appconfig.WARN)

    def test_getExportErrorDefault(self):
        self.assertEqual(self.cfgdef.getExportError(),
            appconfig.ABORT)

    def test_getExportCVSDir(self):
        self.assertEqual(self.cfg.getExportCVSDir(),
            '/path/to/directory/for/cvs/checkouts/for/branch/imports')

    def test_requireDirsAbsolutePaths(self):
        badcfg = StringIO('[global]\ngitdir = relative/path')
        self.assertRaises(ValueError, appconfig.AppConfig, badcfg)
        badcfg = StringIO('[global]\nlogdir = relative/path')
        self.assertRaises(ValueError, appconfig.AppConfig, badcfg)
        badcfg = StringIO('[export]\ncvsdir = relative/path')
        self.assertRaises(ValueError, appconfig.AppConfig, badcfg)
