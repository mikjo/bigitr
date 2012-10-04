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

import ConfigParser
import os
from StringIO import StringIO
import tempfile
import testutils

from bigitr import config

class TestConfig(testutils.TestCase):
    def setUp(self):
        self.fd, self.cf = tempfile.mkstemp(suffix='.bigitr')
        file(self.cf, 'r+').write('[foo]\nbar = ${FAKEHOME}\n')
        self.cfg = config.Config(self.cf)
        if 'FAKEHOME' in os.environ:
            self.fakehome = os.environ['FAKEHOME']
        else:
            self.fakehome = None
        os.environ['FAKEHOME'] = '/tmp'

    def tearDown(self):
        os.close(self.fd)
        os.remove(self.cf)
        if self.fakehome:
            os.environ['FAKEHOME'] = self.fakehome
        else:
            os.unsetenv('FAKEHOME')

    def test_openConfig(self):
        self.assertEqual(self.cfg.openConfig(self.cf).read(),
                         '[foo]\nbar = ${FAKEHOME}\n')

    def test_readConfig(self):
        self.cfg.readConfig(os.fdopen(os.dup(self.fd)))
        self.assertEqual(self.cfg.sections(), ['foo'])

    def test_getEnv(self):
        self.assertEqual(self.cfg.get('foo', 'bar'), '/tmp')

    def test_getGlobalFallbackNoGlobalSection(self):
        self.assertEqual('/tmp', self.cfg.getGlobalFallback('foo', 'bar'))

    def test_getGlobalFallbackDefaultNoGlobalSection(self):
        self.assertEqual(None, self.cfg.getGlobalFallback('asdf', 'b', error=False))
        self.assertEqual('def', self.cfg.getGlobalFallback('asdf', 'b', error=False, defaultValue='def'))

    def test_getGlobalFallbackError(self):
        self.assertRaises(ConfigParser.NoOptionError,
            self.cfg.getGlobalFallback, 'foo', 'b')

    def test_getGlobalFallbackGlobalSection(self):
        self.cfg.add_section('GLOBAL')
        self.cfg.set('GLOBAL', 'b', 'foo')
        self.assertEqual('foo', self.cfg.getGlobalFallback('asdf', 'b'))

    def test_getDefault(self):
        self.assertEqual('/tmp', self.cfg.getDefault('foo', 'bar', 'asdf'))
        self.assertEqual('asdf', self.cfg.getDefault('foo', 'baz', 'asdf'))

    def test_getGlobalDefault(self):
        self.assertEqual('/tmp', self.cfg.getGlobalDefault('foo', 'bar', 'asdf'))
        self.assertEqual('asdf', self.cfg.getGlobalDefault('foo', 'baz', 'asdf'))
        self.cfg.add_section('GLOBAL')
        self.cfg.set('GLOBAL', 'b', 'foo')
        self.assertEqual('foo', self.cfg.getGlobalDefault('a', 'b', 'asdf'))
        self.assertEqual('asdf', self.cfg.getGlobalDefault('a', 'baz', 'asdf'))

    def test_getOptional(self):
        self.assertEqual('/tmp', self.cfg.getOptional('foo', 'bar'))
        self.assertEqual(None, self.cfg.getOptional('foo', 'baz'))

    def test_itemsEnv(self):
        self.assertEqual(self.cfg.items('foo'), [('bar', '/tmp')])

    def test_requireAbsolutePathsFromEnvironment(self):
        cfgstr = StringIO('[foo]\nbardir = ${FAKEHOME}/blah\n')
        cfg = config.Config(cfgstr)
        # asserts both that there is no ValueError and correct interpolation
        self.assertEqual(cfg.get('foo', 'bardir'), '/tmp/blah')

    def test_requireDirAbsolutePaths(self):
        badcfg = StringIO('[foo]\nbardir = baz\n')
        self.assertRaises(ValueError, config.Config, badcfg)

    def test_requireOtherAbsolutePaths(self):
        badcfg = StringIO('[foo]\nbar = baz\n')
        cfg = config.Config(badcfg)
        self.assertRaises(ValueError, cfg.requireAbsolutePaths, 'bar', 'blah')
