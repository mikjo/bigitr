import mock
import os
from StringIO import StringIO
import tempfile
import testutils

from gitcvs import cvsimport, context

class CVSImportTest(testutils.TestCase):
    def setUp(self):
        with mock.patch('gitcvs.log.Log') as mocklog:
            with mock.patch('gitcvs.log.LogCache') as mocklogcache:
                appConfig = StringIO('[global]\n'
                                     'logdir = /logdir\n'
                                     'gitdir = /gitdir\n'
                                     '[export]\n'
                                     'cvsdir = /cvsdir\n')
                repConfig = StringIO('[repo]\n'
                                     'cvsroot = asdf\n'
                                     'cvspath = Some/Loc\n'
                                     'cvs.b1 = b1\n'
                                     'merge.cvs-b1 = b1\n'
                                     'merge.b1 = master\n'
                                     '[repo2]\n'
                                     'cvsroot = fdsa\n'
                                     'cvspath = Other/Loc\n'
                                     'cvs.b1 = b1\n'
                                     'cvs.b2 = b2\n'
                                     'merge.cvs-b1 = b1 b2\n'
                                     'merge.cvs-b2 = b2\n'
                                     )
                self.ctx = context.Context(appConfig, repConfig)
                self.mocklog = mocklog()
                self.imp = cvsimport.Importer(self.ctx)

                #self.importcvs = self.imp.importcvs
                #self.imp.importcvs = mock.Mock()

    def tearDown(self):
        #self.imp.importcvs = self.importcvs
        pass

    # tests importBranches thoroughly
    def test_importAll(self):
        with mock.patch.object(self.imp, 'importcvs'):
            self.imp.importAll()
            self.imp.importcvs.assert_has_calls(
                [mock.call('repo', mock.ANY, mock.ANY, 'b1', 'cvs-b1'),
                 mock.call('repo2', mock.ANY, mock.ANY, 'b1', 'cvs-b1'),
                 mock.call('repo2', mock.ANY, mock.ANY, 'b2', 'cvs-b2')])

    def test_merge(self):
        Git = mock.Mock()
        Git.mergeDefault.return_value = 0
        rc = self.imp.merge('repo2', Git, 'cvs-b1')
        Git.checkout.assert_has_calls([mock.call('b1'), mock.call('b2')])
        Git.mergeFastForward.assert_has_calls(
            [mock.call('origin/b1'), mock.call('origin/b2')])
        Git.mergeDefault.assert_has_calls(
            [mock.call('cvs-b1', "Automated merge 'cvs-b1' into 'b1'"),
             mock.call('cvs-b1', "Automated merge 'cvs-b1' into 'b2'")])
        Git.push.assert_has_calls(
            [mock.call('origin', 'b1', 'b1'),
             mock.call('origin', 'b2', 'b2')]
        )
        self.assertTrue(rc)
        Git.reset_mock()
        rc = self.imp.merge('repo2', Git, 'cvs-b2')
        Git.checkout.assert_called_once_with('b2')
        Git.mergeDefault.assert_called_once_with(
            'cvs-b2', "Automated merge 'cvs-b2' into 'b2'")
        Git.push.assert_called_once_with('origin', 'b2', 'b2')
        self.assertTrue(rc)

    def test_mergeFailure(self):
        Git = mock.Mock()
        Git.mergeDefault.return_value = 1
        rc = self.imp.merge('repo2', Git, 'cvs-b1')
        Git.checkout.assert_has_calls([mock.call('b1'), mock.call('b2')])
        self.assertFalse(rc)

    def test_mergeCascade(self):
        Git = mock.Mock()
        Git.mergeDefault.return_value = 0
        rc = self.imp.merge('repo', Git, 'cvs-b1')
        Git.checkout.assert_has_calls([mock.call('b1'), mock.call('master')])
        self.assertTrue(rc)

    def test_mergeFailureNoCascade(self):
        Git = mock.Mock()
        Git.mergeDefault.return_value = 1
        rc = self.imp.merge('repo', Git, 'cvs-b1')
        Git.checkout.assert_called_once_with('b1') # not 'master'
        self.assertFalse(rc)

    def test_mergeFailureInCascade(self):
        Git = mock.Mock()
        Git.mergeDefault.return_value = 0
        Git.mergeDefault.side_effect = lambda x, y: x == 'b1'
        rc = self.imp.merge('repo', Git, 'cvs-b1')
        Git.checkout.assert_has_calls([mock.call('b1'), mock.call('master')])
        Git.push.assert_called_once_with('origin', 'b1', 'b1') # not 'master'
        self.assertFalse(rc)

    # importcvs tested only by story testing
