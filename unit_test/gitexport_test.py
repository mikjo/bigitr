import mock
import os
from StringIO import StringIO
import tempfile
import testutils

from gitcvs import gitexport, context

class GitExportTest(testutils.TestCase):
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
                                     'git.master = b1\n'
                                     '[repo2]\n'
                                     'cvsroot = fdsa\n'
                                     'cvspath = Other/Loc\n'
                                     'git.b1 = b1\n'
                                     'git.master = b2\n'
                                     )
                self.ctx = context.Context(appConfig, repConfig)
                self.mocklog = mocklog()
                self.exp = gitexport.Exporter(self.ctx, self.username)

    def tearDown(self):
        pass

    # tests exportBranches thoroughly
    def test_exportAll(self):
        with mock.patch.object(self.exp, 'exportgit'):
            self.exp.exportAll()
            self.exp.exportgit.assert_has_calls(
                [mock.call('repo', mock.ANY, mock.ANY, 'b1', 'export-master'),
                 mock.call('repo2', mock.ANY, mock.ANY, 'b2', 'export-master'),
                 mock.call('repo2', mock.ANY, mock.ANY, 'b1', 'export-b1')])

    # exportgit tested only by story testing
