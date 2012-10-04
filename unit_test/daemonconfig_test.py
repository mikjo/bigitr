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

from bigitr import daemonconfig

class TestDaemonConfig(testutils.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(suffix='.bigitr')
        os.environ['DDIR'] = self.dir
        daemonConfig = self.dir + '/daemon'
        file(daemonConfig, 'w').write('''
[GLOBAL]
appconfig = ${DDIR}/app
[foo]
repoconfig = ${DDIR}/foo1.* ${DDIR}/foo2.*
[bar]
appconfig = ${DDIR}/app2
repoconfig = ${DDIR}/bar
email = other@other blah@blah
''')
        self.cfg = daemonconfig.DaemonConfig(daemonConfig)

    def tearDown(self):
        self.removeRecursive(self.dir)
        os.unsetenv('DDIR')

    def test_parallelConversions(self):
        self.assertEqual(1, self.cfg.parallelConversions())
        self.cfg.set('GLOBAL', 'parallel', '8')
        self.assertEqual(8, self.cfg.parallelConversions())

    def test_getPollFrequency(self):
        self.assertEqual(300, self.cfg.getPollFrequency())
        self.cfg.set('GLOBAL', 'pollfrequency', '1h')
        self.assertEqual(3600, self.cfg.getPollFrequency())

    def test_getFullSyncFrequency(self):
        self.assertEqual(86000, self.cfg.getFullSyncFrequency())
        self.cfg.set('GLOBAL', 'syncfrequency', '1h')
        self.assertEqual(3600, self.cfg.getFullSyncFrequency())

    def test_getEmail(self):
        self.assertEqual(None, self.cfg.getEmail())
        self.cfg.set('GLOBAL', 'email', 'here@here')
        self.assertEqual(['here@here'], self.cfg.getEmail())

    def test_getMailFrom(self):
        self.assertEqual(None, self.cfg.getMailFrom())
        self.cfg.set('GLOBAL', 'mailfrom', 'noreply@here')
        self.assertEqual('noreply@here', self.cfg.getMailFrom())

    def test_getMailAll(self):
        self.assertFalse(self.cfg.getMailAll())
        self.cfg.set('GLOBAL', 'mailall', 'true')
        self.assertTrue(self.cfg.getMailAll())

    def test_getSmartHost(self):
        self.assertEqual('localhost', self.cfg.getSmartHost())
        self.cfg.set('GLOBAL', 'smarthost', 'foo')
        self.assertEqual('foo', self.cfg.getSmartHost())

    def test_getApplicationContexts(self):
        self.assertEqual(set(('foo', 'bar')), self.cfg.getApplicationContexts())

    def test_getAppConfig(self):
        self.assertEqual(self.dir + '/app', self.cfg.getAppConfig('foo'))
        self.assertEqual(self.dir + '/app2', self.cfg.getAppConfig('bar'))

    def test_getRepoConfigs(self):
        # files have to exist to be globbed
        file(self.dir + '/foo1.1', 'w')
        file(self.dir + '/foo1.2', 'w')
        file(self.dir + '/foo2.1', 'w')
        file(self.dir + '/bar', 'w')
        self.assertEqual([self.dir + '/foo1.1',
                          self.dir + '/foo1.2',
                          self.dir + '/foo2.1'], self.cfg.getRepoConfigs('foo'))
        self.assertEqual([self.dir + '/bar'], self.cfg.getRepoConfigs('bar'))

    def test_parseTimeSpec(self):
        self.assertEqual(3600, self.cfg._parseTimeSpec('1h'))
        self.assertEqual(3600, self.cfg._parseTimeSpec('1H'))
        self.assertEqual(60, self.cfg._parseTimeSpec('1m'))
        self.assertEqual(60, self.cfg._parseTimeSpec('1M'))
        self.assertEqual(1, self.cfg._parseTimeSpec('1s'))
        self.assertEqual(1, self.cfg._parseTimeSpec('1S'))
        self.assertEqual(1, self.cfg._parseTimeSpec('1'))
        self.assertEqual(3661, self.cfg._parseTimeSpec('1h1m1'))
        self.assertEqual(3612, self.cfg._parseTimeSpec('1h12'))
        self.assertEqual(3661, self.cfg._parseTimeSpec('1h1m1s'))
        self.assertEqual(3661, self.cfg._parseTimeSpec('1h 1m 1s'))
        self.assertEqual(3661, self.cfg._parseTimeSpec('1h 1m 1s '))
        self.assertEqual(3661, self.cfg._parseTimeSpec(' 1h 1m 1s '))

