import mock
from cStringIO import StringIO
import unittest

from gitcvs import git, shell, context

class TestGit(unittest.TestCase):
    def setUp(self):
        with mock.patch('gitcvs.log.Log') as mocklog:
            appConfig = StringIO('[global]\nlogdir = /logs\n')
            repConfig = StringIO('[repo]\n')
            self.ctx = context.Context(appConfig, repConfig)
            self.git = git.Git(self.ctx, 'repo')
            self.mocklog = mocklog()

    def test_clone(self):
        with mock.patch('gitcvs.git.shell.run'):
            uri = '/path/to/repo'
            self.git.clone(uri)
            shell.run.assert_called_once_with(mock.ANY,
                'git', 'clone', uri)

    def test_reset(self):
        with mock.patch('gitcvs.git.shell.run'):
            self.git.reset()
            shell.run.assert_called_once_with(mock.ANY,
                'git', 'reset', '--hard', 'HEAD')

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


    def test_refs(self):
        with mock.patch('gitcvs.git.shell.read') as r:
            r.return_value = (0, '''
a44dfd94fd9de6c27f739274f2fae99ab83fa2f5 refs/heads/master
fe9a5fbf7fe7ca3f6f08946187e2d1ce302c0201 refs/remotes/origin/HEAD
fe9a5fbf7fe7ca3f6f08946187e2d1ce302c0201 refs/remotes/origin/master
''')
            refs = self.git.refs()
            r.assert_called_once_with(mock.ANY,
                'git', 'show-ref', error=False)
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
                'git', 'show-ref', error=False)
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
                'git', 'checkout', 'b')

    def test_listContentFiles(self):
        with mock.patch('gitcvs.git.shell.read') as r:
            r.return_value = (0, '.gitignore\0foo\0.gitmodules\0bar/baz\0')
            files = self.git.listContentFiles()
            r.assert_called_once_with(mock.ANY,
                'git', 'ls-files', '--exclude-standard', '-z')
            self.assertEquals(files, ['foo', 'bar/baz'])

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
                'git', 'add', '.')

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
            self.git.push('origin', 'master')
            shell.run.assert_called_once_with(mock.ANY,
                'git', 'push', 'origin', 'master')

    def test_logmessages(self):
        with mock.patch('gitcvs.git.shell.read') as r:
            r.return_value = (0, 'a message\n')
            msg = self.git.logmessages('since', 'until')
            shell.read.assert_called_once_with(mock.ANY,
                'git', 'log', 'since..until')
            self.assertEqual(msg, 'a message\n')
