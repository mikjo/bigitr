import mock
import os
from StringIO import StringIO
import tempfile
import testutils

from gitcvs import cvsimport, context

class CVSImportTest(testutils.TestCase):
    def setUp(self):
        self.username = 'janedoe'
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
                                     '[repo2]\n'
                                     'cvsroot = fdsa\n'
                                     'cvspath = Other/Loc\n'
                                     'cvs.b1 = b1\n'
                                     'cvs.b2 = b2\n'
                                     )
                self.ctx = context.Context(appConfig, repConfig)
                self.mocklog = mocklog()
                self.imp = cvsimport.Importer(self.ctx, self.username)

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
                 mock.call('repo2', mock.ANY, mock.ANY, 'b2', 'cvs-b2'),
                 mock.call('repo2', mock.ANY, mock.ANY, 'b1', 'cvs-b1')])


    # importcvs tested only by story testing
