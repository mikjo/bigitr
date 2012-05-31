import logging
import os
from cStringIO import StringIO
import tempfile
import testutils

from gitcvs import shell, log, context

class TestLoggingShell(testutils.TestCase):
    def setUp(self):
        self.logdir = tempfile.mkdtemp(suffix='.gitcvs')
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
        for b, dirs, files in os.walk(self.logdir, topdown=False):
            for f in files:
                os.remove('/'.join((b, f)))
            for d in dirs:
                os.rmdir('/'.join((b, d)))
        os.removedirs(self.logdir)

    def test_Empty(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        s = shell.LoggingShell(l, 'true')
        retcode = s.wait()
        self.assertEqual(retcode, 0)
        l.close()
        thislog = '/'.join((self.logdir, 'repo2'))
        files = os.listdir(thislog)
        for filename in files:
            self.assertEqual(os.stat('/'.join((thislog, filename))).st_size, 0)
        self.assertEqual(len(files), 2)
        self.assertEqual(self.logdata.getvalue(), '')
        self.logdata.truncate(0)

    def test_OutputNoErrors(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        os.write(l.stdout, 'this is a test\n')
        s = shell.LoggingShell(l, 'true')
        retcode = s.wait()
        self.assertEqual(retcode, 0)
        l.close()
        thislog = '/'.join((self.logdir, 'repo2'))
        files = os.listdir(thislog)
        self.assertEqual(len([x for x in files if x.endswith('.log.gz')]), 1)
        self.assertEqual(len([x for x in files if x.endswith('.err')]), 1)
        self.assertEqual(len(files), 2)
        sizes = set(os.stat('/'.join((thislog, x))).st_size for x in files)
        self.assertEqual(len(sizes), 2)
        self.assertEqual(self.logdata.getvalue(), '')
        self.logdata.truncate(0)

    def test_ErrorAndStandardOutput(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        os.write(l.stdout, 'this is a test of standard output\n')
        # warning of bad exit code will write to stderr
        s = shell.LoggingShell(l, 'false', error=False)
        retcode = s.wait()
        self.assertEqual(retcode, 1)
        l.close()
        thislog = '/'.join((self.logdir, 'repo2'))
        files = os.listdir(thislog)
        self.assertEqual(len([x for x in files if x.endswith('.err.gz')]), 1)
        self.assertEqual(len([x for x in files if x.endswith('.log.gz')]), 1)
        self.assertEqual(len(files), 2)
        sizes = set(os.stat('/'.join((thislog, x))).st_size for x in files)
        self.assertTrue(0 not in sizes)
        self.assertTrue(self.logdata.getvalue().endswith(
            '\ncommand returned exit code 1\n\n'))
        self.logdata.truncate(0)

    def test_ErrorOutput(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        # warning of bad exit code will write to stderr
        s = shell.LoggingShell(l, 'false', error=False)
        retcode = s.wait()
        self.assertEqual(retcode, 1)
        l.close()
        thislog = '/'.join((self.logdir, 'repo2'))
        files = os.listdir(thislog)
        self.assertEqual(len([x for x in files if x.endswith('.err.gz')]), 1)
        self.assertEqual(len([x for x in files if x.endswith('.log')]), 1)
        self.assertEqual(len(files), 2)
        sizes = set(os.stat('/'.join((thislog, x))).st_size for x in files)
        self.assertEqual(len(sizes), 2)
        self.assertTrue(self.logdata.getvalue().endswith(
            '\ncommand returned exit code 1\n\n'))
        self.logdata.truncate(0)

    def test_RaiseError(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        s = shell.LoggingShell(l, 'false')
        self.assertRaises(ValueError, s.wait)
        l.close()
        self.logdata.truncate(0)

    def test_runRaiseError(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        self.assertRaises(ValueError, shell.run, l, 'false')
        l.close()
        self.logdata.truncate(0)

    def test_readRaiseError(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        self.assertRaises(ValueError, shell.read, l, 'false')
        l.close()
        self.logdata.truncate(0)

    def test_run(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        # warning of bad exit code will write to stderr
        retcode = shell.run(l, 'false', error=False)
        self.assertEqual(retcode, 1)
        l.close()
        thislog = '/'.join((self.logdir, 'repo2'))
        files = os.listdir(thislog)
        self.assertEqual(len([x for x in files if x.endswith('.err.gz')]), 1)
        self.assertEqual(len([x for x in files if x.endswith('.log')]), 1)
        self.assertEqual(len(files), 2)
        sizes = set(os.stat('/'.join((thislog, x))).st_size for x in files)
        self.assertEqual(len(sizes), 2)
        self.assertTrue(self.logdata.getvalue().endswith(
            '\ncommand returned exit code 1\n\n'))
        self.logdata.truncate(0)
        
    def test_readWithData(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        # warning of bad exit code will write to stderr
        retcode, output = shell.read(l, 'echo', 'foo')
        self.assertEqual(retcode, 0)
        self.assertEqual(output, 'foo\n')
        l.close()
        thislog = '/'.join((self.logdir, 'repo2'))
        files = os.listdir(thislog)
        self.assertEqual(len([x for x in files if x.endswith('.err')]), 1)
        # captured output not in log file
        self.assertEqual(len([x for x in files if x.endswith('.log')]), 1)
        self.assertEqual(len(files), 2)
        sizes = set(os.stat('/'.join((thislog, x))).st_size for x in files)
        self.assertEqual(len(sizes), 1)
        self.assertEqual(self.logdata.getvalue(), '')
        self.logdata.truncate(0)
        
