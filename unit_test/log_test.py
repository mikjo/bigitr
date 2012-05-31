from cStringIO import StringIO
import os
import tempfile
import testutils

from gitcvs import log, context

class TestLog(testutils.TestCase):
    def setUp(self):
        self.logdir = tempfile.mkdtemp(suffix='.gitcvs')
        appConfig = StringIO('''
[global]
logdir = %s''' %self.logdir)

        repConfig = StringIO('''
[Path/To/Git/repo1]
[Path/To/Git/repo2]
''')
        self.ctx = context.Context(appConfig, repConfig)

    def tearDown(self):
        for b, dirs, files in os.walk(self.logdir, topdown=False):
            for f in files:
                os.remove('/'.join((b, f)))
            for d in dirs:
                os.rmdir('/'.join((b, d)))
        os.removedirs(self.logdir)

    def test_Empty(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        l.close()
        thislog = '/'.join((self.logdir, 'repo2'))
        files = os.listdir(thislog)
        for filename in files:
            self.assertEqual(os.stat('/'.join((thislog, filename))).st_size, 0)
        self.assertEqual(len(files), 2)

    def test_OutputNoErrors(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        os.write(l.stdout, 'this is a test\n')
        l.close()
        thislog = '/'.join((self.logdir, 'repo2'))
        files = os.listdir(thislog)
        self.assertEqual(len([x for x in files if x.endswith('.log.gz')]), 1)
        self.assertEqual(len([x for x in files if x.endswith('.err')]), 1)
        self.assertEqual(len(files), 2)
        sizes = set(os.stat('/'.join((thislog, x))).st_size for x in files)
        self.assertEqual(len(sizes), 2)

    def test_ErrorAndStandardOutput(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        os.write(l.stdout, 'this is a test of standard output\n')
        os.write(l.stderr, 'this is a test of error output\n')
        l.close()
        thislog = '/'.join((self.logdir, 'repo2'))
        files = os.listdir(thislog)
        self.assertEqual(len([x for x in files if x.endswith('.err.gz')]), 1)
        self.assertEqual(len([x for x in files if x.endswith('.log.gz')]), 1)
        self.assertEqual(len(files), 2)
        sizes = set(os.stat('/'.join((thislog, x))).st_size for x in files)
        self.assertTrue(0 not in sizes)

    def test_ErrorOutput(self):
        l = log.Log(self.ctx, 'Path/To/Git/repo2', None)
        os.write(l.stderr, 'this is a test\n')
        l.close()
        thislog = '/'.join((self.logdir, 'repo2'))
        files = os.listdir(thislog)
        self.assertEqual(len([x for x in files if x.endswith('.err.gz')]), 1)
        self.assertEqual(len([x for x in files if x.endswith('.log')]), 1)
        self.assertEqual(len(files), 2)
        sizes = set(os.stat('/'.join((thislog, x))).st_size for x in files)
        self.assertEqual(len(sizes), 2)

    def test_LogCache(self):
        c = log.LogCache(self.ctx)
        l1 = c['Path/To/Git/repo1']
        l2 = c['Path/To/Git/repo2']
        self.assertEqual(os.path.basename(os.path.dirname(l1.thislog)),
                         'repo1')
        self.assertEqual(os.path.basename(os.path.dirname(l2.thislog)),
                         'repo2')
        self.assertEqual(len(c), 2)
        l1.close()
        self.assertEqual(len(c), 1)
