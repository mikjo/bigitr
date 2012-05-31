import os
from StringIO import StringIO
import tempfile
import testutils

from gitcvs import config

class TestConfig(testutils.TestCase):
    def setUp(self):
        self.fd, self.cf = tempfile.mkstemp(suffix='.gitcvs')
        file(self.cf, 'r+').write('[foo]')
        self.cfg = config.Config(self.cf)

    def tearDown(self):
        os.close(self.fd)
        os.remove(self.cf)

    def test_openConfig(self):
        self.assertEqual(self.cfg.openConfig(self.cf).read(), '[foo]')

    def test_readConfig(self):
        self.cfg.readConfig(os.fdopen(os.dup(self.fd)))
        self.assertEqual(self.cfg.sections(), ['foo'])

    def test_requireDirAbsolutePaths(self):
        badcfg = StringIO('[foo]\nbardir = baz\n')
        self.assertRaises(ValueError, config.Config, badcfg)

    def test_requireOtherAbsolutePaths(self):
        badcfg = StringIO('[foo]\nbar = baz\n')
        cfg = config.Config(badcfg)
        self.assertRaises(ValueError, cfg.requireAbsolutePaths, 'bar', 'blah')
