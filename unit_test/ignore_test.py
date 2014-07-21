#
# Copyright 2014 SAS Institute
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
import mock
import os
import tempfile
import testutils

from bigitr import ignore

class TestIgnore(testutils.TestCase):
    def setUp(self):
        self.logdir = tempfile.mkdtemp(suffix='.bigitr')
        self.log = mock.Mock()
        self.codedir = tempfile.mkdtemp(suffix='.bigitr')
        self.ignorefile = self.codedir + '/ignore'

    def tearDown(self):
        self.removeRecursive(self.logdir)
        self.removeRecursive(self.codedir)

    @mock.patch('bigitr.ignore.Ignore.parse')
    def test_empty_init(self, parse):
        i = ignore.Ignore(self.log, self.ignorefile)
        self.assertEquals(i.ignores, None)
        self.assertEquals(i.fileName, os.path.basename(self.ignorefile))
        self.assertEquals(self.log, i.log)
        parse.assert_called_once_with(self.ignorefile)

    def test_init(self):
        file(self.ignorefile, 'w').write('*.o\n#comment\n/path/to/foo\n')
        i = ignore.Ignore(self.log, self.ignorefile)
        self.assertEquals(i.ignores, ['*.o', '/path/to/foo'])
        self.assertEquals(i.fileName, os.path.basename(self.ignorefile))

    @mock.patch('os.write')
    def test_match(self, write):
        i = ignore.Ignore(self.log, self.ignorefile)
        self.assertEquals(i.match('*.o', ['foo.c', 'foo.o']),
            set(('foo.o',)))
        write.assert_called_once_with(mock.ANY,
            'ignore: *.o ignores file foo.o\n')
        write.reset_mock()
        self.assertEquals(i.match('/path/*.o', ['foo.o', '/path/foo.o']),
            set(('/path/foo.o',)))
        write.assert_called_once_with(mock.ANY,
            'ignore: /path/*.o ignores file /path/foo.o\n')

    def test_filter(self):
        file(self.ignorefile, 'w').write('*.o\n/path/to/foo\n/dir/foo.o\n')
        logFile = self.logdir + '/log'
        self.log.stderr = os.open(logFile, os.O_CREAT|os.O_RDWR, 0700)
        i = ignore.Ignore(self.log, self.ignorefile)
        i.filter(['foo.c', 'foo.o',
                  '/path/to/foo', '/path/to/bar',
                  '/dir/foo.c', '/dir/foo.o',
        ])
        os.close(self.log.stderr)
        self.assertEquals(file(logFile).readlines(), [
            'ignore: *.o ignores file foo.o\n',
            'ignore: *.o ignores file /dir/foo.o\n',
            'ignore: /path/to/foo ignores file /path/to/foo\n',
            'ignore: /dir/foo.o ignores file /dir/foo.o\n',
        ])
