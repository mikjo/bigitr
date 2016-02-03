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

import gzip
import logging
import mock
import os
from cStringIO import StringIO
import tempfile
import testutils

from bigitr import shell, log, context

class TestLoggingShell(testutils.TestCase):
    def setUp(self):
        self.logdir = tempfile.mkdtemp(suffix='.bigitr')
        appConfig = StringIO('''
[global]
logdir = %s
''' %self.logdir)

        repConfig = StringIO('''
[Path/To/Git/repo2]
''')
        self.ctx = context.Context(appConfig, repConfig)
        self.logdata = StringIO()
        self.handler = logging.StreamHandler(self.logdata)
        logging.getLogger().addHandler(self.handler)

    def tearDown(self):
        logging.getLogger().removeHandler(self.handler)
        self.removeRecursive(self.logdir)

    @mock.patch('subprocess.Popen')
    def test_timestamp(self, P):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        s = shell.LoggingShell(l, 'ignoreme')
        s._tzname = lambda: 'EDT'
        s._now = lambda: 1454508561.227579
        self.assertEqual(s.timestamp(), '[Wed Feb 03 09:09:21.2276 EDT 2016]')

    def test_Empty(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        s = shell.LoggingShell(l, 'true')
        self.assertEqual(l.lastOutput(), (None, None))
        self.assertEqual(l.lastError(), None)
        retcode = s.finish()
        self.assertEqual(l.lastOutput(), ('', ''))
        self.assertEqual(l.lastError(), '')
        self.assertEqual(retcode, 0)
        l.close()
        thislog = '/'.join((self.logdir, 'repo2'))
        files = os.listdir(thislog)
        for filename in files:
            filename = '/'.join((thislog, filename))
            self.assertEqual(
                [x for x in gzip.GzipFile(filename).readlines()
                 if not x.startswith('[')],
                [])
        self.assertEqual(len(files), 2)
        self.assertEqual(self.logdata.getvalue(), '')
        self.logdata.truncate(0)

    def test_OutputNoErrors(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        os.write(l.stdout, 'this is a test\n')
        s = shell.LoggingShell(l, 'true')
        retcode = s.finish()
        self.assertEqual(retcode, 0)
        self.assertEqual(l.lastOutput(), ('', ''))
        l.close()
        thislog = '/'.join((self.logdir, 'repo2'))
        files = os.listdir(thislog)
        for filename in files:
            fileName = '/'.join((thislog, filename))
            logLines = gzip.GzipFile(fileName).readlines()
            nonLogLines = [x for x in logLines if not x.startswith('[')]
            if '.log' in filename:
                self.assertEqual(len(nonLogLines), 1)
            else:
                self.assertEqual(len(nonLogLines), 0)
            self.assertTrue(
                logLines[-1].endswith(' COMPLETE with return code: 0\n'))
        self.assertEqual(self.logdata.getvalue(), '')
        self.logdata.truncate(0)

    def test_ErrorAndStandardOutput(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        os.write(l.stdout, 'this is a test of standard output\n')
        # warning of bad exit code will write to stderr
        s = shell.LoggingShell(l, 'false', error=False)
        retcode = s.finish()
        self.assertEqual(retcode, 1)
        self.assertEqual(l.lastOutput(), ('', ''))
        l.close()
        thislog = '/'.join((self.logdir, 'repo2'))
        files = os.listdir(thislog)
        self.assertEqual(len([x for x in files if x.endswith('.err.gz')]), 1)
        self.assertEqual(len([x for x in files if x.endswith('.log.gz')]), 1)
        self.assertEqual(len(files), 2)
        sizes = set(os.stat('/'.join((thislog, x))).st_size for x in files)
        self.assertTrue(0 not in sizes)
        self.assertEqual(self.logdata.getvalue(), '')
        self.logdata.truncate(0)

    def test_ErrorOutput(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        # warning of bad exit code will write to stderr
        s = shell.LoggingShell(l, 'false', error=False)
        retcode = s.finish()
        self.assertEqual(retcode, 1)
        l.close()
        thislog = '/'.join((self.logdir, 'repo2'))
        files = os.listdir(thislog)
        self.assertEqual(len(files), 2)
        for filename in files:
            fileName = '/'.join((thislog, filename))
            logLines = gzip.GzipFile(fileName).readlines()
            nonLogLines = [x for x in logLines if not x.startswith('[')]
            self.assertEqual(len(nonLogLines), 0)
            self.assertTrue(
                logLines[-1].endswith(' COMPLETE with return code: 1\n'))
        self.assertEqual(self.logdata.getvalue(), '')
        self.logdata.truncate(0)

    def test_RaiseError(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        s = shell.LoggingShell(l, 'false')
        self.assertRaises(shell.ErrorExitCode, s.finish)
        l.close()
        self.assertTrue(self.logdata.getvalue().startswith('\n'))
        self.logdata.truncate(0)

    def test_runRaiseError(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        self.assertRaises(shell.ErrorExitCode, shell.run, l, 'false')
        l.close()
        self.assertTrue(self.logdata.getvalue().startswith('\n'))
        self.logdata.truncate(0)

    def test_readRaiseError(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        self.assertRaises(shell.ErrorExitCode, shell.read, l, 'false')
        l.close()
        self.assertTrue(self.logdata.getvalue().startswith('\n'))
        self.logdata.truncate(0)

    def test_run(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        retcode = shell.run(l, 'false', error=False)
        self.assertEqual(retcode, 1)
        l.close()
        thislog = '/'.join((self.logdir, 'repo2'))
        files = os.listdir(thislog)
        for filename in files:
            fileName = '/'.join((thislog, filename))
            logLines = gzip.GzipFile(fileName).readlines()
            nonLogLines = [x for x in logLines if not x.startswith('[')]
            self.assertEqual(len(nonLogLines), 0)
            self.assertTrue(
                logLines[-1].endswith(' COMPLETE with return code: 1\n'))
        self.assertEqual(self.logdata.getvalue(), '')
        self.logdata.truncate(0)
        
    def test_readWithData(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        retcode, output = shell.read(l, 'echo', 'foo')
        self.assertEqual(retcode, 0)
        self.assertEqual(output, 'foo\n')
        self.assertEqual(l.lastOutput(), ('', ''))
        l.close()
        thislog = '/'.join((self.logdir, 'repo2'))
        files = os.listdir(thislog)
        self.assertEqual(len(files), 2)
        for filename in files:
            fileName = '/'.join((thislog, filename))
            logLines = gzip.GzipFile(fileName).readlines()
            nonLogLines = [x for x in logLines if not x.startswith('[')]
            self.assertEqual(len(nonLogLines), 0)
            self.assertTrue(
                logLines[-1].endswith(' COMPLETE with return code: 0\n'))
        self.assertEqual(self.logdata.getvalue(), '')
        self.logdata.truncate(0)
        
    def test_readShellOutputData(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        retcode = shell.run(l, 'echo', 'foo')
        self.assertEqual(retcode, 0)
        self.assertEqual(l.lastOutput(), ('foo\n', ''))

    def test_readShellOutputError(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        retcode = shell.run(l, 'sh', '-c', 'echo bar; echo baz; echo foo >&2 ; exit 1', error=False)
        self.assertEqual(retcode, 1)
        self.assertEqual(l.lastOutput(), ('bar\nbaz\n', 'foo\n'))
        self.assertEqual(l.lastError(), 'foo\n')
        ao = mock.Mock()
        self.ctx.mails['Path/To/Git/repo2'].addOutput = ao
        l.mailLastOutput('broke')
        ao.assert_called_with('broke', 'bar\nbaz\n', 'foo\n')
