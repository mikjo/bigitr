from cStringIO import StringIO
import mock
import os
import tempfile
import testutils

from gitcvs import cvs, shell, context, util

class TestCVS(testutils.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(suffix='.gitcvs')
        self.cdir = tempfile.mkdtemp(suffix='.gitcvs')
        self.fdir = '%s/repo/brnch/Loc' %self.cdir
        os.makedirs(self.fdir)
        if 'CVSROOT' in os.environ:
            self.cvsroot = os.environ['CVSROOT']
        else:
            self.cvsroot = None
        os.unsetenv('CVSROOT')
        with mock.patch('gitcvs.log.Log') as mocklog:
            appConfig = StringIO('[global]\n'
                                 'logdir = /logs\n'
                                 'gitdir = %s\n'
                                 '[export]\n'
                                 'cvsdir = %s\n' %(self.dir, self.cdir))
            repConfig = StringIO('[repo]\n'
                                 'cvsroot = asdf\n'
                                 'cvspath = Some/Loc')
            self.ctx = context.Context(appConfig, repConfig)
            self.cvs = cvs.CVS(self.ctx, 'repo', 'brnch', 'johndoe')
            self.mocklog = mocklog()

    def tearDown(self):
        self.removeRecursive(self.dir)
        self.removeRecursive(self.cdir)
        if self.cvsroot:
            os.environ['CVSROOT'] = self.cvsroot
        else:
            os.unsetenv('CVSROOT')

    def test_setEnvironment(self):
        self.cvs.setEnvironment()
        self.assertEqual(os.environ['CVSROOT'],
            self.ctx.getCVSRoot('repo', 'johndoe'))

    def test_listContentFiles(self):
        fdir = '%s/repo/brnch/Loc' %self.cdir
        cdir = '%s/CVS' %fdir
        os.makedirs(cdir)
        os.makedirs(fdir+'/dir')
        file(cdir+'/ignoreme', 'w')
        file(fdir+'/includeme', 'w')
        file(fdir+'/dir/metoo', 'w')
        files = self.cvs.listContentFiles()
        self.assertEqual(files, ['includeme', 'dir/metoo'])

    def test_export(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.cvs.export('targetdir')
            shell.run.assert_called_once_with(mock.ANY,
                'cvs', 'export', '-d', 'targetdir', '-r', 'brnch', 'Some/Loc')
            self.assertEqual(os.environ['CVSROOT'],
                self.ctx.getCVSRoot('repo', 'johndoe'))

    def test_cleanKeywords(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.cvs.cleanKeywords(['a'])
            shell.run.assert_called_once_with(mock.ANY,
                'sed', '-i', '-r', mock.ANY, 'a')

    def test_checkout(self):
        with mock.patch('gitcvs.git.shell.run'):
            with mock.patch.multiple('os', getcwd=mock.DEFAULT,
                                           chdir=mock.DEFAULT):
                self.cvs.checkout()
                shell.run.assert_called_once_with(mock.ANY,
                    'cvs', 'checkout', '-d', 'repo',
                    '-r', 'brnch', 'Some/Loc')
                self.assertEqual(os.environ['CVSROOT'],
                    self.ctx.getCVSRoot('repo', 'johndoe'))
                os.getcwd.assert_called_once_with()
                self.assertEqual(os.chdir.call_count, 2)
                os.chdir.assert_any_call(os.getcwd())
                os.chdir.assert_any_call('%s/repo/brnch' %self.cdir)

    def test_update(self):
        with mock.patch('gitcvs.git.shell.run'):
            with mock.patch.multiple('os', getcwd=mock.DEFAULT,
                                           chdir=mock.DEFAULT):
                self.cvs.update()
                shell.run.assert_called_once_with(mock.ANY,
                    'cvs', 'update', '-d')
                os.getcwd.assert_called_once_with()
                self.assertEqual(os.chdir.call_count, 2)
                os.chdir.assert_any_call(os.getcwd())
                os.chdir.assert_any_call('%s/repo/brnch/Loc' %self.cdir)

    def test_deleteFiles(self):
        with mock.patch('gitcvs.git.shell.run'):
            with mock.patch.multiple('os', getcwd=mock.DEFAULT,
                                           chdir=mock.DEFAULT,
                                           remove=mock.DEFAULT):
                self.cvs.deleteFiles(['/a', '/b/c', '/b/d'])
                shell.run.assert_called_once_with(mock.ANY,
                    'cvs', 'remove', '/a', '/b/c', '/b/d')
                os.getcwd.assert_called_once_with()
                self.assertEqual(os.chdir.call_count, 2)
                os.chdir.assert_any_call(os.getcwd())
                os.chdir.assert_any_call('%s/repo/brnch/Loc' %self.cdir)
                self.assertEqual(os.remove.call_count, 3)
                os.remove.assert_has_calls([
                    mock.call('/a'),
                    mock.call('/b/c'),
                    mock.call('/b/d'),
                ])

    def test_deleteFilesEmpty(self):
        with mock.patch('gitcvs.git.shell.run'):
            with mock.patch.multiple('os', getcwd=mock.DEFAULT,
                                           chdir=mock.DEFAULT,
                                           remove=mock.DEFAULT):
                self.cvs.deleteFiles([])
                self.assertFalse(shell.run.called)
                self.assertFalse(os.remove.called)

    def test_copyFiles(self):
        with mock.patch('gitcvs.util.copyFiles'):
            fileList = ['/a', '/b', '/dir/metoo']
            self.cvs.copyFiles(self.dir, fileList)
            util.copyFiles.assertCalled(self.dir, self.cvs.path, fileList)

    def test_copyFilesEmpty(self):
        with mock.patch('os.path.exists'):
            self.cvs.copyFiles('/ignore', [])
            self.assertFalse(os.path.exists.called)

    def test_addDirectories(self):
        with mock.patch('gitcvs.git.shell.run'):
            with mock.patch('os.path.exists'):
                # if CVS directories exist
                os.path.exists.return_value = True
                self.cvs.addDirectories(['a', 'b', 'dir/metoo'])
                self.assertFalse(shell.run.called)
                # if CVS directories do not exist
                os.path.exists.return_value = False
                self.cvs.addDirectories(['a', 'b', 'dir/metoo'])
                shell.run.assert_has_calls([
                    mock.call(mock.ANY, 'cvs', 'add', 'a'),
                    mock.call(mock.ANY, 'cvs', 'add', 'b'),
                    mock.call(mock.ANY, 'cvs', 'add', 'dir'),
                    mock.call(mock.ANY, 'cvs', 'add', 'dir/metoo'),
                ])
                shell.run.reset_mock()
                # make sure absolute paths do not recurse
                os.path.exists.return_value = False
                self.cvs.addDirectories(['/a', '/b', '/dir/metoo'])
                shell.run.assert_has_calls([
                    mock.call(mock.ANY, 'cvs', 'add', '/a'),
                    mock.call(mock.ANY, 'cvs', 'add', '/b'),
                    mock.call(mock.ANY, 'cvs', 'add', '/dir'),
                    mock.call(mock.ANY, 'cvs', 'add', '/dir/metoo'),
                ])

    def test_addFiles(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.cvs.addFiles(['/a', '/b', '/dir/metoo'])
            shell.run.assert_called_once_with(mock.ANY,
                'cvs', 'add', '/a', '/b', '/dir/metoo')

    def test_addFilesEmpty(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.cvs.addFiles([])
            self.assertFalse(shell.run.called)

    def test_commit(self):
        with mock.patch('gitcvs.git.shell.run'):
            with mock.patch.multiple('os', remove=mock.DEFAULT,
                                           close=mock.DEFAULT,
                                           write=mock.DEFAULT) as mockos:
                with mock.patch('tempfile.mkstemp') as mockmkstemp:
                    mockmkstemp.return_value = (123456789, '/notThere')
                    self.cvs.commit('commitMessage')
                    mockos['write'].assert_called_once_with(123456789, 'commitMessage')
                    mockmkstemp.assert_called_once_with('.gitcvs')
                    shell.run.assert_called_once_with(mock.ANY,
                        'cvs', 'commit', '-r', 'brnch', '-R', '-F', '/notThere')
                    mockos['remove'].assert_called_once_with('/notThere')
                    mockos['close'].assert_called_once_with(123456789)
