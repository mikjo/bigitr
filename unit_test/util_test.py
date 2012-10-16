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
import tempfile
import testutils

from bigitr import util

class TestUtil(testutils.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(suffix='.bigitr')
        self.s = self.d + '/s'
        self.t = self.d + '/t'
        os.mkdir(self.s)
        os.mkdir(self.t)
        os.makedirs(self.s+'/dir')
        file(self.s+'/a', 'w').write('a')
        file(self.s+'/b', 'w').write('b')
        file(self.s+'/dir/metoo', 'w').write('metoo')

    def tearDown(self):
        self.removeRecursive(self.d)

    def test_copyFiles(self):
        util.copyFiles(self.s, self.t, ['/a', '/b', '/dir/metoo'])
        self.assertTrue(os.path.exists(self.t + '/a'))
        self.assertTrue(os.path.exists(self.t + '/b'))
        self.assertTrue(os.path.exists(self.t + '/dir/metoo'))
        self.assertEqual(file(self.t + '/a').read(), 'a')
        self.assertEqual(file(self.t + '/b').read(), 'b')
        self.assertEqual(file(self.t + '/dir/metoo').read(), 'metoo')

    def test_copyTree(self):
        util.copyTree(self.s, self.t)
        self.assertTrue(os.path.exists(self.t + '/a'))
        self.assertTrue(os.path.exists(self.t + '/b'))
        self.assertTrue(os.path.exists(self.t + '/dir/metoo'))
        self.assertEqual(file(self.t + '/a').read(), 'a')
        self.assertEqual(file(self.t + '/b').read(), 'b')
        self.assertEqual(file(self.t + '/dir/metoo').read(), 'metoo')

    def test_removeRecursive(self):
        util.removeRecursive(self.s)
        self.assertEqual(util.listFiles(self.s), [])

    def test_copyFilesEmpty(self):
        with mock.patch('os.path.exists'):
            util.copyFiles('/ignore', '/me', [])
            self.assertFalse(os.path.exists.called)

    def test_listFiles(self):
        self.assertEqual(sorted(util.listFiles(self.s)),
                         ['a', 'b', 'dir/metoo'])

    def test_saveDir(self):
        O = object()
        @util.saveDir
        def inner(foo):
            return O
        with mock.patch('os.chdir') as C:
            self.assertEquals(inner(1), O)
            C.assert_has_call(os.getcwd())

    def test_saveDirException(self):
        @util.saveDir
        def inner(foo):
            [][0]
        with mock.patch('os.chdir') as C:
            self.assertRaises(IndexError, inner, 1)
            C.assert_has_call(os.getcwd())

    def test_fileName(self):
        try:
            os.environ['FOO'] = 'bar'
            self.assertEqual(util.fileName('~/${FOO}'), os.environ['HOME']+'/bar')
        finally:
            os.unsetenv('FOO')

    def test_killExists(self):
        self.assertTrue(util.kill(os.getpid(), 0))

    def test_killDoesNotExist(self):
        self.assertFalse(util.kill(123456789, 0)) # 32K is max pid
