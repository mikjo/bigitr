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

import mock
import os
from cStringIO import StringIO

import testutils

import bigitr
from bigitr import context
from bigitr import cvsimport
from bigitr import git
from bigitr import gitexport
from bigitr import gitmerge
from bigitr import shell
from bigitr import sync

class TestRunner(testutils.TestCase):
    def setUp(self):
        self.foo = os.getenv('FOO')
        os.environ['FOO'] = '/foo'
        self.home = os.getenv('HOME')
        os.environ['HOME'] = '/hm'

    def tearDown(self):
        if self.foo is None:
            os.unsetenv('FOO')
        else:
            os.environ['FOO'] = self.foo
        if self.home is None:
            os.unsetenv('HOME')
        else:
            os.environ['HOME'] = self.home

    @mock.patch('bigitr._Runner._init_runner')
    def test_runner(self, IR):
        with mock.patch('bigitr.context.Context') as C:
            r = bigitr._Runner('~/.bigitr', '${FOO}/repoconf', ['repo1', 'repo2'])
            C.assert_called_once_with('/hm/.bigitr', '/foo/repoconf')
            self.assertEqual(r.appconfig, '~/.bigitr')
            self.assertEqual(r.config, '${FOO}/repoconf')
            self.assertEqual(r.repos, ['repo1', 'repo2'])
            self.assertEqual(r.ctx, C('/hm/.bigitr', '/foo/repoconf'))

    @mock.patch('bigitr._Runner._init_runner')
    def test_getContext(self, IR):
        with mock.patch('bigitr.context.Context') as C:
            with mock.patch('bigitr.util.fileName') as F:
                r = bigitr._Runner('~/.bigitr', '${FOO}/repoconf', [])
                C.assert_called_once_with(F(), F())

    @mock.patch('bigitr._Runner.__init__')
    def test_unimplementedInitRunner(self, I):
        I.return_value = None
        r = bigitr._Runner(mock.Mock())
        self.assertRaises(NotImplementedError, r._init_runner)

    @mock.patch('bigitr.util.fileName')
    @mock.patch('bigitr._Runner._init_runner')
    @mock.patch('bigitr._Runner.__init__')
    def test_expandFilenameIfString(self, I, IR, F):
        I.return_value = None
        r = bigitr._Runner(mock.Mock())
        self.assertEqual(1, r.expandFilenameIfString(1))
        self.assertTrue(isinstance(r.expandFilenameIfString('b'), mock.Mock))

    @mock.patch('bigitr._Runner._init_runner')
    def test_getBranchMapsWithDefault(self, IR):
        with mock.patch('bigitr._Runner.getContext') as C:
            r = bigitr._Runner('~/.bigitr', '${FOO}/repoconf', [])
            r.ctx.getRepositories.return_value = ['foo']
            r.ctx.getRepositoryByName.side_effect = lambda x: x
            l = r.getBranchMaps()
            self.assertEqual(l, [['foo', None]])
            r.ctx.getRepositories.assert_called_once_with()

    @mock.patch('bigitr._Runner._init_runner')
    def test_getBranchMapsWithName(self, IR):
        with mock.patch('bigitr._Runner.getContext') as C:
            r = bigitr._Runner('~/.bigitr', '${FOO}/repoconf', ['foo'])
            r.ctx.getRepositoryByName.return_value = '/foo'
            l = r.getBranchMaps()
            self.assertEqual(l, [['/foo', None]])
            r.ctx.getRepositoryByName.assert_called_once_with('foo')

    @mock.patch('bigitr._Runner._init_runner')
    def test_getBranchMapsWithBadName(self, IR):
        with mock.patch('bigitr._Runner.getContext') as C:
            r = bigitr._Runner('~/.bigitr', '${FOO}/repoconf', ['dne'])
            r.ctx.getRepositoryByName.side_effect = lambda x: {}[x]
            self.assertRaises(KeyError, r.getBranchMaps)
            r.ctx.getRepositoryByName.assert_called_once_with('dne')


    @mock.patch('bigitr._Runner._init_runner')
    def test_getBranchMapsWithBranches(self, IR):
        with mock.patch('bigitr._Runner.getContext') as C:
            r = bigitr._Runner('~/.bigitr', '${FOO}/repoconf',
                               ['repo::b1', 'repo2::b2', 'repo::3::'])
            r.ctx.getRepositoryByName.side_effect = lambda x: x
            l = r.getBranchMaps()
            self.assertEqual(l, [['repo', 'b1'], ['repo2', 'b2'], ['repo::3', '']])
            r.ctx.getRepositories.assert_not_called()
            r.ctx.getRepositoryByName.assert_has_calls([
                mock.call('repo'),
                mock.call('repo2'),
                mock.call('repo::3')])

    def runProcessWithSideEffect(self, side_effect=None):
        with mock.patch('bigitr.git.Git') as G:
            with mock.patch('bigitr._Runner.__init__') as I:
                I.return_value = None
                with mock.patch('bigitr._Runner.getBranchMaps') as R:
                    R.return_value = [['repo', None]]
                    r = bigitr._Runner(mock.Mock(), mock.Mock(), mock.Mock())
                    r.ctx = mock.Mock()
                    r.runner = mock.Mock()
                    r.do = mock.Mock()
                    g = G(r.ctx, 'repo')
                    if side_effect is not None:
                        r.do.side_effect = side_effect
                    r.process()
                    r.do.assert_called_once_with('repo', g, requestedBranch=None)
                    return r.runner, g

    @mock.patch('bigitr._Runner._init_runner')
    def test_process(self, IR):
        c, g = self.runProcessWithSideEffect()
        c.err.report.assert_not_called()
        g.log.mailLastOutput.assert_not_called()

    @mock.patch('bigitr._Runner._init_runner')
    def test_processShellError(self, IR):
        def raiseShellError():
            raise shell.ErrorExitCode(1)
        c, g = self.runProcessWithSideEffect(lambda *x, **z: raiseShellError())
        c.err.report.assert_called_once_with('repo')
        g.log.mailLastOutput.assert_called_once_with(mock.ANY)


    @mock.patch('bigitr._Runner._init_runner')
    def test_processOtherError(self, IR):
        c, g = self.runProcessWithSideEffect(lambda *x, **z: {}[1])
        c.err.report.assert_called_once_with('repo')
        g.log.mailLastOutput.assert_not_called()


    @mock.patch('bigitr._Runner.getContext')
    @mock.patch('bigitr._Runner._init_runner')
    def test_close(self, IR, C):
        r = bigitr._Runner('~/.bigitr', '${FOO}/repoconf', [])
        l = mock.Mock()
        r.ctx.logs.values.return_value = [l]
        r.close()
        l.close.assert_called_once_with()


@mock.patch('bigitr.sync.Synchronizer')
@mock.patch('bigitr._Runner.__init__')
@mock.patch('bigitr.git.Git')
class TestSynchronize(testutils.TestCase):
    def test_run(self, G, R, S):
        R.return_value = None
        s = bigitr.Synchronize('a', 'c', 'r')
        self.assertEquals(s.poll, False)
        s.ctx = mock.Mock()
        s.repos = ['foo::bar']
        s.close = mock.Mock()
        s._init_runner()
        s.run()
        S.assert_called_once_with(s.ctx)
        S().synchronize.assert_called_once_with(mock.ANY, mock.ANY)
        s.close.assert_called_once_with()

    @mock.patch('os.chdir')
    def test_runPollNew(self, C, G, R, S):
        R.return_value = None
        s = bigitr.Synchronize('a', 'c', 'r', poll=True)
        self.assertEquals(s.poll, True)
        s.ctx = mock.Mock()
        s.ctx.getGitDir.return_value = '/imp'
        s.repos = ['foo::bar']
        G().repo = 'foo'
        s.ctx.getRepositoryName.return_value = 'foo'
        s.close = mock.Mock()
        s._init_runner()
        with mock.patch('os.path.exists') as E:
            E.return_value = False
            s.run()
            E.assert_has_call('/imp/foo')
        C.assert_called_once_with(os.getcwd())
        G().refs.assert_not_called()
        G().fetch.assert_not_called()
        S.assert_called_once_with(s.ctx)
        S().synchronize.assert_called_once_with(mock.ANY, mock.ANY)
        s.close.assert_called_once_with()

    @mock.patch('os.chdir')
    def test_runPollNoChange(self, C, G, R, S):
        R.return_value = None
        s = bigitr.Synchronize('a', 'c', 'r', poll=True)
        self.assertEquals(s.poll, True)
        s.ctx = mock.Mock()
        s.ctx.getGitDir.return_value = '/imp'
        s.repos = ['foo::bar']
        G().repo = 'foo'
        s.ctx.getRepositoryName.return_value = 'foo'
        s.close = mock.Mock()
        s._init_runner()
        G().refs.side_effect = [set(('1', '2')), set(('1', '2'))]
        with mock.patch('os.path.exists') as E:
            s.run()
            E.assert_has_call('/imp/foo')
        C.assert_has_calls(
            [mock.call('/imp/foo'),
             mock.call(os.getcwd())])
        self.assertEqual(C.call_count, 2)
        G().fetch.assert_called_once_with()
        S.assert_called_once_with(s.ctx)
        S().synchronize.assert_not_called()
        s.close.assert_called_once_with()

    @mock.patch('os.chdir')
    def test_runPollNoChangeWithNewDefault(self, C, G, R, S):
        R.return_value = None
        s = bigitr.Synchronize('a', 'c', 'r', poll=False)
        self.assertEquals(s.poll, False)
        s.ctx = mock.Mock()
        s.ctx.getGitDir.return_value = '/imp'
        s.repos = ['foo::bar']
        G().repo = 'foo'
        s.ctx.getRepositoryName.return_value = 'foo'
        s.close = mock.Mock()
        s._init_runner()
        G().refs.side_effect = [set(('1', '2')), set(('1', '2'))]
        with mock.patch('os.path.exists') as E:
            s.run(poll=True)
            E.assert_has_call('/imp/foo')
        C.assert_has_calls(
            [mock.call('/imp/foo'),
             mock.call(os.getcwd())])
        self.assertEqual(C.call_count, 2)
        G().fetch.assert_called_once_with()
        S.assert_called_once_with(s.ctx)
        S().synchronize.assert_not_called()
        s.close.assert_called_once_with()


    @mock.patch('os.chdir')
    def test_runPollWithChange(self, C, G, R, S):
        R.return_value = None
        s = bigitr.Synchronize('a', 'c', 'r', poll=True)
        self.assertEquals(s.poll, True)
        s.ctx = mock.Mock()
        s.ctx.getGitDir.return_value = '/imp'
        s.repos = ['foo::bar']
        G().repo = 'foo'
        s.ctx.getRepositoryName.return_value = 'foo'
        s.close = mock.Mock()
        s._init_runner()
        G().refs.side_effect = [set(('1', '2')), set(('1', '3'))]
        with mock.patch('os.path.exists') as E:
            s.run()
            E.assert_has_call('/imp/foo')
        C.assert_has_calls(
            [mock.call('/imp/foo'),
             mock.call(os.getcwd())])
        self.assertEqual(C.call_count, 2)
        G().fetch.assert_called_once_with()
        S.assert_called_once_with(s.ctx)
        S().synchronize.assert_called_once_with(mock.ANY, mock.ANY)
        s.close.assert_called_once_with()


class TestImport(testutils.TestCase):
    @mock.patch('bigitr.cvsimport.Importer')
    @mock.patch('bigitr._Runner.__init__')
    @mock.patch('bigitr.git.Git')
    def test_run(self, G, R, I):
        R.return_value = None
        i = bigitr.Import()
        i.ctx = mock.Mock()
        i.repos = ['foo::bar']
        i.close = mock.Mock()
        i._init_runner()
        i.run()
        I.assert_called_once_with(i.ctx)
        I().importBranches.assert_called_once_with(mock.ANY, mock.ANY,
            requestedBranch='bar')
        i.close.assert_called_once_with()


class TestExport(testutils.TestCase):
    @mock.patch('bigitr.gitexport.Exporter')
    @mock.patch('bigitr._Runner.__init__')
    @mock.patch('bigitr.git.Git')
    def test_run(self, G, R, E):
        R.return_value = None
        e = bigitr.Export()
        e.ctx = mock.Mock()
        e.repos = ['foo::bar']
        e.close = mock.Mock()
        e._init_runner()
        e.run()
        E.assert_called_once_with(e.ctx)
        E().exportBranches.assert_called_once_with(mock.ANY, mock.ANY,
            requestedBranch='bar')
        e.close.assert_called_once_with()

class TestMerge(testutils.TestCase):
    @mock.patch('bigitr.gitmerge.Merger')
    @mock.patch('bigitr._Runner.__init__')
    @mock.patch('bigitr.git.Git')
    def test_run(self, G, R, M):
        R.return_value = None
        m = bigitr.Merge()
        m.ctx = mock.Mock()
        m.repos = ['foo::bar']
        m.close = mock.Mock()
        m._init_runner()
        m.run()
        M.assert_called_once_with(m.ctx)
        M().mergeBranches.assert_called_once_with(mock.ANY, mock.ANY,
            requestedBranch='bar')
        m.close.assert_called_once_with()

class TestMain(testutils.TestCase):
    def test_help(self):
        with mock.patch('bigitr.sync.Synchronizer') as S:
            with mock.patch('sys.stdout') as E:
                self.assertRaises(SystemExit, bigitr.main, ['-h'])
                S.assert_not_called()
                help_text = E.write.call_args_list[0][0][0]
                self.assertTrue('\nSynchronize Git and CVS\n' in help_text)
                self.assertTrue('\n  -h, --help            show this help message and exit\n' in help_text)

    def test_helpCommand(self):
        with mock.patch('bigitr.sync.Synchronizer') as S:
            with mock.patch('sys.stdout') as E:
                self.assertRaises(SystemExit, bigitr.main, ['help'])
                S.assert_not_called()
                help_text = E.write.call_args_list[0][0][0]
                self.assertTrue('\nSynchronize Git and CVS\n' in help_text)
                self.assertTrue('\n  -h, --help            show this help message and exit\n' in help_text)

    def test_badcommand(self):
        with mock.patch('bigitr.sync.Synchronizer') as S:
            with mock.patch('sys.stdout') as E:
                self.assertRaises(SystemExit, bigitr.main, ['badcommand'])
                S.assert_not_called()
                help_text = E.write.call_args_list[0][0][0]
                self.assertTrue('\nSynchronize Git and CVS\n' in help_text)
                self.assertTrue('\n  -h, --help            show this help message and exit\n' in help_text)

    def test_syncCommand(self):
        with mock.patch('bigitr.Synchronize') as S:
            self.assertRaises(SystemExit, bigitr.main, ['sync'])
            S().run.assert_called_once_with()
            S.reset_mock()
            self.assertRaises(SystemExit, bigitr.main, ['sync', 'repo1', 'repo2'])
            S('repo1', 'repo2').run.assert_called_once_with()

    def test_importCommand(self):
        with mock.patch('bigitr.Import') as I:
            self.assertRaises(SystemExit, bigitr.main, ['import'])
            I().run.assert_called_once_with()
            I.reset_mock()
            self.assertRaises(SystemExit, bigitr.main, ['import', 'r1', 'r2'])
            I('r1', 'r2').run.assert_called_once_with()

    def test_exportCommand(self):
        with mock.patch('bigitr.Export') as E:
            self.assertRaises(SystemExit, bigitr.main, ['export'])
            E().run.assert_called_once_with()
            E.reset_mock()
            self.assertRaises(SystemExit, bigitr.main, ['export', 'r1'])
            E('r1').run.assert_called_once_with()

    def test_mergeCommand(self):
        with mock.patch('bigitr.Merge') as M:
            self.assertRaises(SystemExit, bigitr.main, ['merge'])
            M().run.assert_called_once_with()
            M.reset_mock()
            self.assertRaises(SystemExit, bigitr.main, ['merge', 'r1::branch'])
            M('r1::branch').run.assert_called_once_with()
