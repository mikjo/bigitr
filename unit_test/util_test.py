import mock
import os
import tempfile
import testutils

from gitcvs import util

class TestUtil(testutils.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(suffix='.gitcvs')
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

    def test_copyFilesEmpty(self):
        with mock.patch('os.path.exists'):
            util.copyFiles('/ignore', '/me', [])
            self.assertFalse(os.path.exists.called)
