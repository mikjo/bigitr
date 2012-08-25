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

import gitcvs
from gitcvs import context
from gitcvs import cvsimport
from gitcvs import git
from gitcvs import gitexport
from gitcvs import gitmerge
from gitcvs import sync

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

    def test_runner(self):
        with mock.patch('gitcvs.context.Context') as C:
            args = mock.Mock(appconfig='~/.bigitr',
                             config='${FOO}/repoconf',
                             repository=[['repo1', 'repo2']])
            r = gitcvs._Runner(args)
            C.assert_called_once_with('/hm/.bigitr', '/foo/repoconf')
            self.assertEqual(args, r.args)
            self.assertEqual(r.repos, ['repo1', 'repo2'])
            self.assertEqual(r.ctx, C('/hm/.bigitr', '/foo/repoconf'))

    def test_getBranchMapsWithDefault(self):
        with mock.patch('gitcvs._Runner.getContext') as C:
            args = mock.Mock(repository=[[]])
            r = gitcvs._Runner(args)
            r.ctx.getRepositories.return_value = ['foo']
            r.ctx.getRepositoryByName.side_effect = lambda x: x
            l = r.getBranchMaps()
            self.assertEqual(l, [['foo', None]])
            r.ctx.getRepositories.assert_called_once_with()
            self.assertEqual(args, r.args)

    def test_getBranchMapsWithName(self):
        with mock.patch('gitcvs._Runner.getContext') as C:
            args = mock.Mock(repository=[['foo']])
            r = gitcvs._Runner(args)
            r.ctx.getRepositoryByName.return_value = '/foo'
            l = r.getBranchMaps()
            self.assertEqual(l, [['/foo', None]])
            r.ctx.getRepositoryByName.assert_called_once_with('foo')

    def test_getBranchMapsWithBadName(self):
        with mock.patch('gitcvs._Runner.getContext') as C:
            args = mock.Mock(repository=[['dne']])
            r = gitcvs._Runner(args)
            r.ctx.getRepositoryByName.side_effect = lambda x: {}[x]
            self.assertRaises(KeyError, r.getBranchMaps)
            r.ctx.getRepositoryByName.assert_called_once_with('dne')


    def test_getBranchMapsWithBranches(self):
        with mock.patch('gitcvs._Runner.getContext') as C:
            args = mock.Mock(repository=[['repo::b1', 'repo2::b2', 'repo::3::']])
            r = gitcvs._Runner(args)
            r.ctx.getRepositoryByName.side_effect = lambda x: x
            l = r.getBranchMaps()
            self.assertEqual(l, [['repo', 'b1'], ['repo2', 'b2'], ['repo::3', '']])
            r.ctx.getRepositories.assert_not_called()
            r.ctx.getRepositoryByName.assert_has_calls([
                mock.call('repo'),
                mock.call('repo2'),
                mock.call('repo::3')])

    def test_unimplementedRun(self):
        with mock.patch('gitcvs._Runner.__init__') as I:
            I.return_value = None
            r = gitcvs._Runner(mock.Mock())
            self.assertRaises(NotImplementedError, r.run)

    def test_process(self):
        with mock.patch('gitcvs.git.Git') as G:
            with mock.patch('gitcvs._Runner.__init__') as I:
                I.return_value = None
                with mock.patch('gitcvs._Runner.getBranchMaps') as R:
                    R.return_value = [['repo', None]]
                    r = gitcvs._Runner(mock.Mock())
                    r.ctx = mock.Mock()
                    c = mock.Mock()
                    f = mock.Mock()
                    r.process(c, f)
                    f.assert_called_once_with('repo', G(r.ctx, 'repo'), requestedBranch=None)
                    c.err.report.assert_not_called()
                    f.reset_mock()
                    f.side_effect = lambda x, y: {}[1]
                    r.process(c, f)
                    f.assert_called_once_with('repo', G(r.ctx, 'repo'), requestedBranch=None)
                    c.err.report.assert_called_once_with('repo')

    def test_close(self):
        with mock.patch('gitcvs._Runner.getContext') as C:
            args = mock.Mock(repository=[[]])
            r = gitcvs._Runner(args)
            l = mock.Mock()
            r.ctx.logs.values.return_value = [l]
            r.close()
            l.close.assert_called_once_with()

class TestSynchronize(testutils.TestCase):
    def test_run(self):
        with mock.patch('gitcvs._Runner.__init__') as R:
            R.return_value = None
            with mock.patch('gitcvs.sync.Synchronizer') as S:
                s = gitcvs.Synchronize(mock.Mock())
                s.ctx = mock.Mock()
                s.process = mock.Mock()
                s.close = mock.Mock()
                s.run()
                S.assert_called_once_with(s.ctx)
                s.process.assert_called_once_with(S(), mock.ANY) # lambda
                s.close.assert_called_once_with()

class TestImport(testutils.TestCase):
    def test_run(self):
        with mock.patch('gitcvs._Runner.__init__') as R:
            R.return_value = None
            with mock.patch('gitcvs.cvsimport.Importer') as I:
                i = gitcvs.Import(mock.Mock())
                i.ctx = mock.Mock()
                i.process = mock.Mock()
                i.close = mock.Mock()
                i.run()
                I.assert_called_once_with(i.ctx)
                i.process.assert_called_once_with(I(), I().importBranches)
                i.close.assert_called_once_with()


class TestExport(testutils.TestCase):
    def test_run(self):
        with mock.patch('gitcvs._Runner.__init__') as R:
            R.return_value = None
            with mock.patch('gitcvs.gitexport.Exporter') as E:
                e = gitcvs.Export(mock.Mock())
                e.ctx = mock.Mock()
                e.process = mock.Mock()
                e.close = mock.Mock()
                e.run()
                E.assert_called_once_with(e.ctx)
                e.process.assert_called_once_with(E(), E().exportBranches)
                e.close.assert_called_once_with()


class TestMerge(testutils.TestCase):
    def test_run(self):
        with mock.patch('gitcvs._Runner.__init__') as R:
            R.return_value = None
            with mock.patch('gitcvs.gitmerge.Merger') as M:
                m = gitcvs.Merge(mock.Mock())
                m.ctx = mock.Mock()
                m.process = mock.Mock()
                m.close = mock.Mock()
                m.run()
                M.assert_called_once_with(m.ctx)
                m.process.assert_called_once_with(M(), M().mergeBranches)
                m.close.assert_called_once_with()


class TestMain(testutils.TestCase):
    def test_help(self):
        with mock.patch('gitcvs.sync.Synchronizer') as S:
            with mock.patch('sys.stdout') as E:
                self.assertRaises(SystemExit, gitcvs.main, ['-h'])
                S.assert_not_called()
                help_text = E.write.call_args_list[0][0][0]
                self.assertTrue('\nSynchronize Git and CVS\n' in help_text)
                self.assertTrue('\n  -h, --help            show this help message and exit\n' in help_text)

    def test_helpCommand(self):
        with mock.patch('gitcvs.sync.Synchronizer') as S:
            with mock.patch('sys.stdout') as E:
                self.assertRaises(SystemExit, gitcvs.main, ['help'])
                S.assert_not_called()
                help_text = E.write.call_args_list[0][0][0]
                self.assertTrue('\nSynchronize Git and CVS\n' in help_text)
                self.assertTrue('\n  -h, --help            show this help message and exit\n' in help_text)

    def test_badcommand(self):
        with mock.patch('gitcvs.sync.Synchronizer') as S:
            with mock.patch('sys.stdout') as E:
                self.assertRaises(SystemExit, gitcvs.main, ['badcommand'])
                S.assert_not_called()
                help_text = E.write.call_args_list[0][0][0]
                self.assertTrue('\nSynchronize Git and CVS\n' in help_text)
                self.assertTrue('\n  -h, --help            show this help message and exit\n' in help_text)

    def test_syncCommand(self):
        with mock.patch('gitcvs.Synchronize') as S:
            self.assertRaises(SystemExit, gitcvs.main, ['sync'])
            S().run.assert_called_once_with()
            S.reset_mock()
            self.assertRaises(SystemExit, gitcvs.main, ['sync', 'repo1', 'repo2'])
            S('repo1', 'repo2').run.assert_called_once_with()

    def test_importCommand(self):
        with mock.patch('gitcvs.Import') as I:
            self.assertRaises(SystemExit, gitcvs.main, ['import'])
            I().run.assert_called_once_with()
            I.reset_mock()
            self.assertRaises(SystemExit, gitcvs.main, ['import', 'r1', 'r2'])
            I('r1', 'r2').run.assert_called_once_with()

    def test_exportCommand(self):
        with mock.patch('gitcvs.Export') as E:
            self.assertRaises(SystemExit, gitcvs.main, ['export'])
            E().run.assert_called_once_with()
            E.reset_mock()
            self.assertRaises(SystemExit, gitcvs.main, ['export', 'r1'])
            E('r1').run.assert_called_once_with()

    def test_mergeCommand(self):
        with mock.patch('gitcvs.Merge') as M:
            self.assertRaises(SystemExit, gitcvs.main, ['merge'])
            M().run.assert_called_once_with()
            M.reset_mock()
            self.assertRaises(SystemExit, gitcvs.main, ['merge', 'r1::branch'])
            M('r1::branch').run.assert_called_once_with()
