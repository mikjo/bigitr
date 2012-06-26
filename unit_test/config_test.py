import os
from StringIO import StringIO
import tempfile
import testutils

from gitcvs import config

class TestConfig(testutils.TestCase):
    def setUp(self):
        self.fd, self.cf = tempfile.mkstemp(suffix='.gitcvs')
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
