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
from cStringIO import StringIO
import testutils

from gitcvs import git, shell, context

class TestGit(testutils.TestCase):
    def setUp(self):
        with mock.patch('gitcvs.log.Log') as mocklog:
            appConfig = StringIO('[global]\n'
                                 'logdir = /logs\n'
                                 'gitdir = /git\n'
                                 '[import]\n'
                                 'cvsdir = /cvs\n'
                                 '\n')
            repConfig = StringIO('[repo]\n'
                                 'gitroot = git@host\n'
                                 'cvspath = sub/module\n'
                                 'prehook.git = precommand arg\n'
                                 'posthook.git = postcommand arg\n'
                                 'prehook.git.brnch = precommand brnch\n'
                                 'posthook.git.brnch = postcommand brnch\n'
                                 'prehook.imp.git = preimpcommand arg\n'
                                 'posthook.imp.git = postimpcommand arg\n'
                                 'prehook.imp.git.brnch = preimpcommand brnch\n'
                                 'posthook.imp.git.brnch = postimpcommand brnch\n'
                                 'prehook.exp.git = preexpcommand arg\n'
                                 'posthook.exp.git = postexpcommand arg\n'
                                 'prehook.exp.git.brnch = preexpcommand brnch\n'
                                 'posthook.exp.git.brnch = postexpcommand brnch\n'
                                 '\n')
            self.ctx = context.Context(appConfig, repConfig)
            self.git = git.Git(self.ctx, 'repo')
            self.mocklog = mocklog()

    def test_clone(self):
        with mock.patch('gitcvs.git.shell.run'):
            uri = '/path/to/repo'
            self.git.clone(uri)
            shell.run.assert_called_once_with(mock.ANY,
                'git', 'clone', uri)

    def test_fetch(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.git.fetch()
            shell.run.assert_called_once_with(mock.ANY,
                'git', 'fetch', '--all')

    def test_reset(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.git.reset()
            shell.run.assert_called_once_with(mock.ANY,
                'git', 'reset', '--hard', 'HEAD')

    def test_clean(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.git.clean()
            shell.run.assert_called_once_with(mock.ANY,
                'git', 'clean', '--force', '-x', '-d')

    def test_pristine(self):
        with mock.patch.multiple(self.git, statusIgnored=mock.DEFAULT,
                                        clean=mock.DEFAULT,
                                        refs=mock.DEFAULT,
                                        reset=mock.DEFAULT) as mockgit:
            mockgit['statusIgnored'].return_value = True
            mockgit['refs'].return_value = [('ignore', 'HEAD')]
            self.git.pristine()
            mockgit['statusIgnored'].assert_called_once_with()
            mockgit['clean'].assert_called_once_with()
            mockgit['refs'].assert_called_once_with()
            mockgit['reset'].assert_called_once_with()

    def test_branches(self):
        with mock.patch('gitcvs.git.shell.read') as r:
            r.return_value = (0, '''
* master
  remotes/origin/HEAD -> origin/master
  remotes/origin/master
''')
            branches = self.git.branches()
            r.assert_called_once_with(mock.ANY,
                'git', 'branch', '-a')
            self.assertEquals(branches, set((
                'master',
                'remotes/origin/HEAD',
                'remotes/origin/master',
            )))

    def test_branchesNone(self):
        with mock.patch('gitcvs.git.shell.read') as r:
            r.return_value = (0, '')
            branches = self.git.branches()
            r.assert_called_once_with(mock.ANY,
                'git', 'branch', '-a')
            self.assertEquals(branches, set())

    def test_branch(self):
        with mock.patch('gitcvs.git.shell.read') as r:
            r.return_value = (0, '''
* master
  other
''')
            branch = self.git.branch()
            r.assert_called_once_with(mock.ANY,
                'git', 'branch')
            self.assertEquals(branch, 'master')

    def test_branchOther(self):
        with mock.patch('gitcvs.git.shell.read') as r:
            r.return_value = (0, '''
  master
* other
''')
            branch = self.git.branch()
            r.assert_called_once_with(mock.ANY,
                'git', 'branch')
            self.assertEquals(branch, 'other')

    def test_refs(self):
        with mock.patch('gitcvs.git.shell.read') as r:
            r.return_value = (0, '''
a44dfd94fd9de6c27f739274f2fae99ab83fa2f5 refs/heads/master
fe9a5fbf7fe7ca3f6f08946187e2d1ce302c0201 refs/remotes/origin/HEAD
fe9a5fbf7fe7ca3f6f08946187e2d1ce302c0201 refs/remotes/origin/master
''')
            refs = self.git.refs()
            r.assert_called_once_with(mock.ANY,
                'git', 'show-ref', '--head', error=False)
            self.assertEquals(refs, [
                ('a44dfd94fd9de6c27f739274f2fae99ab83fa2f5',
                 'refs/heads/master'),
                ('fe9a5fbf7fe7ca3f6f08946187e2d1ce302c0201',
                 'refs/remotes/origin/HEAD'),
                ('fe9a5fbf7fe7ca3f6f08946187e2d1ce302c0201',
                 'refs/remotes/origin/master')
            ])

    def test_refsNone(self):
        with mock.patch('gitcvs.git.shell.read') as r:
            r.return_value = (1, '')
            refs = self.git.refs()
            r.assert_called_once_with(mock.ANY,
                'git', 'show-ref', '--head', error=False)
            self.assertEquals(refs, None)


    def test_newBranch(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.git.newBranch('b')
            self.assertEqual(shell.run.call_args_list[0][0][1:],
                ('git', 'branch', 'b'))
            self.assertEqual(shell.run.call_args_list[1][0][1:],
                ('git', 'push', '--set-upstream', 'origin', 'b'))
            self.assertEqual(shell.run.call_count, 2)

    def test_trackBranch(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.git.trackBranch('b')
            shell.run.assert_called_once_with(mock.ANY,
                'git', 'branch', '--track', 'b', 'origin/b')

    def test_checkoutTracking(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.git.checkoutTracking('b')
            shell.run.assert_called_once_with(mock.ANY,
                'git', 'checkout', '--track', 'origin/b')

    def test_checkoutNewImportBranch(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.git.checkoutNewImportBranch('b')
            self.assertEqual(shell.run.call_args_list[0][0][1:],
                ('git', 'checkout', '--orphan', 'b'))
            self.assertEqual(shell.run.call_args_list[1][0][1:],
                ('git', 'rm', '-rf', '.'))
            self.assertEqual(shell.run.call_count, 2)

    def test_checkout(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.git.checkout('b')
            shell.run.assert_called_once_with(mock.ANY,
                'git', 'checkout', '-f', 'b')

    def test_listContentFiles(self):
        with mock.patch('gitcvs.git.shell.read') as r:
            r.return_value = (0, '.gitignore\0foo\0.gitmodules\0bar/baz\0')
            files = self.git.listContentFiles()
            r.assert_called_once_with(mock.ANY,
                'git', 'ls-files', '--exclude-standard', '-z')
            self.assertEquals(files, ['foo', 'bar/baz'])

    def test_statusEmpty(self):
        with mock.patch('gitcvs.git.shell.read') as r:
            r.return_value = (0, '')
            status = self.git.status()
            r.assert_called_once_with(mock.ANY,
                'git', 'status', '--porcelain')
            self.assertEquals(status, '')

    def test_status(self):
        with mock.patch('gitcvs.git.shell.read') as r:
            r.return_value = (0, ''' M gitcvs/cvsimport.py
 M gitcvs/git.py
''')
            status = self.git.status()
            r.assert_called_once_with(mock.ANY,
                'git', 'status', '--porcelain')
            self.assertEquals(status, ''' M gitcvs/cvsimport.py
 M gitcvs/git.py
''')

    def test_statusIgnoredEmpty(self):
        with mock.patch('gitcvs.git.shell.read') as r:
            r.return_value = (0, '')
            status = self.git.statusIgnored()
            r.assert_called_once_with(mock.ANY,
                'git', 'status', '--porcelain', '--ignored')
            self.assertEquals(status, '')

    def test_statusIgnored(self):
        with mock.patch('gitcvs.git.shell.read') as r:
            r.return_value = (0, ''' M gitcvs/cvsimport.py
 M gitcvs/git.py
''')
            status = self.git.statusIgnored()
            r.assert_called_once_with(mock.ANY,
                'git', 'status', '--porcelain', '--ignored')
            self.assertEquals(status, ''' M gitcvs/cvsimport.py
 M gitcvs/git.py
''')


    def test_infoStatus(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.git.infoStatus()
            shell.run.assert_called_once_with(mock.ANY,
                'git', 'status')

    def test_infoDiff(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.git.infoDiff()
            shell.run.assert_called_once_with(mock.ANY,
                'git', 'diff', '--stat=200',
                '--patch', '--minimal', '--irreversible-delete')

    def test_infoDiffFrom(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.git.infoDiff('from')
            shell.run.assert_called_once_with(mock.ANY,
                'git', 'diff', '--stat=200',
                '--patch', '--minimal', '--irreversible-delete',
                'from..HEAD')

    def test_infoDiffFromTo(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.git.infoDiff('from', 'to')
            shell.run.assert_called_once_with(mock.ANY,
                'git', 'diff', '--stat=200',
                '--patch', '--minimal', '--irreversible-delete',
                'from..to')

    def test_addAll(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.git.addAll()
            shell.run.assert_called_once_with(mock.ANY,
                'git', 'add', '-A', '.')

    def test_mergeDefault(self):
        with mock.patch('gitcvs.git.shell.run'):
            shell.run.return_value = 0
            rc = self.git.mergeDefault('brnch', 'msg')
            shell.run.assert_called_once_with(mock.ANY,
                'git', 'merge', 'brnch', '-m', 'msg', error=False)
            self.assertEqual(rc, 0)

    def test_mergeDefaultFailure(self):
        with mock.patch('gitcvs.git.shell.run'):
            shell.run.return_value = 1
            rc = self.git.mergeDefault('brnch', 'msg')
            shell.run.assert_called_once_with(mock.ANY,
                'git', 'merge', 'brnch', '-m', 'msg', error=False)
            self.assertEqual(rc, 1)

    def test_mergeFastForward(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.git.mergeFastForward('brnch')
            shell.run.assert_called_once_with(mock.ANY,
                'git', 'merge', '--ff', '--ff-only', 'brnch')

    def test_mergeIgnore(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.git.mergeIgnore('b')
            shell.run.assert_called_once_with(mock.ANY,
                'git', 'merge', '--strategy=ours', '--ff',
                '-m', 'branch "b" closed', 'b')

    def test_commit(self):
        with mock.patch('gitcvs.git.shell.run'):
            message = 'message'
            self.git.commit(message)
            shell.run.assert_called_once_with(mock.ANY,
                'git', 'commit', '-m', message)

    def test_push(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.git.push('origin', 'master', 'master')
            shell.run.assert_called_once_with(mock.ANY,
                'git', 'push', 'origin', 'master:master')

    def test_logmessages(self):
        with mock.patch('gitcvs.git.shell.read') as r:
            r.return_value = (0, 'a message\n')
            msg = self.git.logmessages('since', 'until')
            shell.read.assert_called_once_with(mock.ANY,
                'git', 'log', 'since..until')
            self.assertEqual(msg, 'a message\n')

    def test_initializeGitRepositoryWithCreateNoSkel(self):
        foo = []
        def inner():
            exists.side_effect = [False, True]
            refs.return_value = None
            self.git.initializeGitRepository()
            chdir.assert_has_calls([mock.call('/git'),
                                    mock.call('/git/repo')])
            exists.assert_has_calls([mock.call('/git/repo'),
                                     mock.call('/cvs/repo/module/.cvsignore')])
            clone.assert_called_once_with('git@host:repo')
            refs.assert_called_once_with()
            addAll.assert_called_once_with()
            commit.assert_called_once_with('create new empty master branch')
            push.assert_called_once_with('origin', 'master', 'master')
            lF.assert_not_called()
            cF.assert_not_called()

        with mock.patch('os.path.exists') as exists:
            with mock.patch('os.chdir') as chdir:
                with mock.patch('gitcvs.git.Git.clone') as clone:
                    with mock.patch('gitcvs.git.Git.refs') as refs:
                        with mock.patch('gitcvs.git.Git.addAll') as addAll:
                            with mock.patch('gitcvs.git.Git.commit') as commit:
                                with mock.patch('gitcvs.git.Git.push') as push:
                                    with mock.patch('gitcvs.util.listFiles') as lF:
                                        with mock.patch('gitcvs.util.copyFiles') as cF:
                                            with mock.patch('__builtin__.file') as mf:
                                                inner()

    def test_initializeGitRepositoryWithCreateWithSkel(self):
        def inner():
            self.ctx._rm.set('repo', 'skeleton', '/skeleton')
            exists.return_value = False
            refs.return_value = None
            self.git.initializeGitRepository()
            chdir.assert_has_calls([mock.call('/git'),
                                    mock.call('/git/repo')])
            exists.assert_has_calls([mock.call('/git/repo')])
            clone.assert_called_once_with('git@host:repo')
            refs.assert_called_once_with()
            addAll.assert_called_once_with()
            commit.assert_called_once_with('create new empty master branch')
            push.assert_called_once_with('origin', 'master', 'master')
            lF.assert_not_called()
            cF.assert_not_called()
            mf.assert_not_called()

        with mock.patch('os.path.exists') as exists:
            with mock.patch('os.chdir') as chdir:
                with mock.patch('gitcvs.git.Git.clone') as clone:
                    with mock.patch('gitcvs.git.Git.refs') as refs:
                        with mock.patch('gitcvs.git.Git.addAll') as addAll:
                            with mock.patch('gitcvs.git.Git.commit') as commit:
                                with mock.patch('gitcvs.git.Git.push') as push:
                                    with mock.patch('gitcvs.util.listFiles') as lF:
                                        with mock.patch('gitcvs.util.copyFiles') as cF:
                                            with mock.patch('__builtin__.file') as mf:
                                                inner()

    def test_initializeGitRepositoryWithNoCreate(self):
        def inner():
            exists.return_value = False
            refs.return_value = None
            self.assertRaises(RuntimeError, self.git.initializeGitRepository, create=False)
            chdir.assert_not_called()

        with mock.patch('os.path.exists') as exists:
            with mock.patch('os.chdir') as chdir:
                with mock.patch('gitcvs.git.Git.clone') as clone:
                    with mock.patch('gitcvs.git.Git.refs') as refs:
                        inner()

    def test_initializeGitRepositoryAlreadyDone(self):
        with mock.patch('os.path.exists') as e:
            with mock.patch('os.chdir') as c:
                e.return_value = True
                self.git.initializeGitRepository()
                c.assert_not_called()

    def test_runImpPreHooks(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.git.runImpPreHooks('brnch')
            shell.run.assert_has_calls([
                mock.call(mock.ANY, 'precommand', 'arg'),
                mock.call(mock.ANY, 'preimpcommand', 'arg'),
                mock.call(mock.ANY, 'precommand', 'brnch'),
                mock.call(mock.ANY, 'preimpcommand', 'brnch'),
            ])

    def test_runImpPostHooks(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.git.runImpPostHooks('brnch')
            shell.run.assert_has_calls([
                mock.call(mock.ANY, 'postcommand', 'arg'),
                mock.call(mock.ANY, 'postimpcommand', 'arg'),
                mock.call(mock.ANY, 'postcommand', 'brnch'),
                mock.call(mock.ANY, 'postimpcommand', 'brnch'),
            ])

    def test_runExpPreHooks(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.git.runExpPreHooks('brnch')
            shell.run.assert_has_calls([
                mock.call(mock.ANY, 'precommand', 'arg'),
                mock.call(mock.ANY, 'preexpcommand', 'arg'),
                mock.call(mock.ANY, 'precommand', 'brnch'),
                mock.call(mock.ANY, 'preexpcommand', 'brnch'),
            ])

    def test_runExpPostHooks(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.git.runExpPostHooks('brnch')
            shell.run.assert_has_calls([
                mock.call(mock.ANY, 'postcommand', 'arg'),
                mock.call(mock.ANY, 'postexpcommand', 'arg'),
                mock.call(mock.ANY, 'postcommand', 'brnch'),
                mock.call(mock.ANY, 'postexpcommand', 'brnch'),
            ])
