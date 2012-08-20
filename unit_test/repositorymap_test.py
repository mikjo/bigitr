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

import ConfigParser
import os
from cStringIO import StringIO
import tempfile
import testutils

from gitcvs import repositorymap

class TestRepositoryConfig(testutils.TestCase):
    def setUp(self):
        os.environ['TESTCVSUSER'] = 'usr'
        self.fd, self.cf = tempfile.mkstemp(suffix='.gitcvs')
        file(self.cf, 'r+').write('''
[GLOBAL]
gitroot = git@host2
cvsroot = :pserver:${TESTCVSUSER}@server2:/path
prehook.git = gitprehook arg
cvsvar.V = default
[Path/To/Git/repository]
gitroot = git@host
cvsroot = :pserver:${TESTCVSUSER}@servername:/path
cvspath = Path/To/CVS/directory
skeleton = /path/to/skeleton
branchfrom = branchroot
cvs.a1 = a1
cvs.a2 = a2
git.master = a2
git.a1 = a1
prefix.a2 = cvs-a2-prefix
cvsvar.V = override
cvsvar.V2 = v2
merge.cvs-a2 = a2 master
merge.cvs-a1 = a1
prehook.git.master = gitmasterprehook
prehook.git.a1 = gita1prehook
posthook.git.master = gitmasterposthook
posthook.git = gitposthook
posthook.cvs.cvs-a1 = cvsa1posthook
email = foo@bar baz@blah

[Path/To/Git/repo2]
cvspath = Path/To/CVS/directory
git.master = a2
prehook.cvs.cvs-a2 = cvsa2prehook "quoted arg"
''')
        self.cfg = repositorymap.RepositoryConfig(self.cf)

        otherfd, self.bad = tempfile.mkstemp(suffix='.gitcvs')
        os.close(otherfd)
        file(self.bad, 'r+').write('''
[Path/To/Git/repository]
[Another/Path/To/Git/repository]
''')

    def tearDown(self):
        os.close(self.fd)
        os.remove(self.cf)
        os.remove(self.bad)

    def test_getDefault(self):
        self.assertEqual(self.cfg.getDefault('Path/To/Git/repository', 'gitroot'),
                         'git@host')
        self.assertEqual(self.cfg.getDefault('Path/To/Git/repo2', 'gitroot'),
                         'git@host2')
        self.assertRaises(ConfigParser.NoOptionError,
                          self.cfg.getDefault, 'Path/To/Git/repo2', 'asdf')
        self.assertEqual(self.cfg.getDefault('Path/To/Git/repo2', 'asdf', error=False), None)

    def test_getRepositories(self):
        self.assertEqual(self.cfg.getRepositories(),
            set(('Path/To/Git/repo2',
                 'Path/To/Git/repository')))

    def test_getRepositoryName(self):
        self.assertEqual(self.cfg.getRepositoryName('Path/To/Git/repo2'),
            'repo2')

    def test_getRepositoryByName(self):
        self.assertEqual(self.cfg.getRepositoryByName('Path/To/Git/repo2'),
            'Path/To/Git/repo2')
        self.assertEqual(self.cfg.getRepositoryByName('repo2'),
            'Path/To/Git/repo2')
        self.assertRaises(KeyError, self.cfg.getRepositoryByName, 'doesnotexist')

    def test_getCVSRoot(self):
        self.assertEqual(self.cfg.getCVSRoot('Path/To/Git/repository'),
                         ':pserver:usr@servername:/path')
    
    def test_getCVSRootDefault(self):
        self.assertEqual(self.cfg.getCVSRoot('Path/To/Git/repo2'),
                         ':pserver:usr@server2:/path')
    
    def test_getGitRef(self):
        self.assertEqual(self.cfg.getGitRef('Path/To/Git/repository'),
                         'git@host:Path/To/Git/repository')

    def test_getGitRefDefault(self):
        self.assertEqual(self.cfg.getGitRef('Path/To/Git/repo2'),
                         'git@host2:Path/To/Git/repo2')

    def test_getCVSPath(self):
        self.assertEqual(self.cfg.getCVSPath('Path/To/Git/repository'),
                         'Path/To/CVS/directory')

    def test_getSkeleton(self):
        self.assertEqual(self.cfg.getSkeleton('Path/To/Git/repository'),
                         '/path/to/skeleton')

    def test_getBranchFrom(self):
        self.assertEqual(self.cfg.getBranchFrom('Path/To/Git/repository'),
                         'branchroot')

    def test_getBranchFromDefault(self):
        self.assertEqual(self.cfg.getBranchFrom('Path/To/Git/repo2'),
                         None)

    def test_getBranchPrefix(self):
        self.assertEqual(self.cfg.getBranchPrefix('Path/To/Git/repository', 'a2'),
                         'cvs-a2-prefix')

    def test_getBranchPrefixDefault(self):
        self.assertEqual(self.cfg.getBranchPrefix('Path/To/Git/repo2', 'a2'),
                         None)

    def test_getImportBranchMaps(self):
        self.assertEqual(self.cfg.getImportBranchMaps('Path/To/Git/repository'),
                         [('a1', 'cvs-a1'), ('a2', 'cvs-a2')])

    def test_getExportBranchMaps(self):
        self.assertEqual(self.cfg.getExportBranchMaps('Path/To/Git/repository'),
                         [('a1', 'a1', 'export-a1'),
                          ('master', 'a2', 'export-master')])

    def test_getCVSVariables(self):
        self.assertEqual(self.cfg.getCVSVariables('Path/To/Git/repository'),
                         ['V=override', 'V2=v2'])
        self.assertEqual(self.cfg.getCVSVariables('Path/To/Git/repo2'),
                         ['V=default'])

    def test_getMergeBranchMaps(self):
        self.assertEqual(self.cfg.getMergeBranchMaps('Path/To/Git/repository'),
                         {'cvs-a2': set(('a2', 'master')),
                          'cvs-a1': set(('a1',))})

    def test_getMergeBranchMapsEmpty(self):
        self.assertEqual(self.cfg.getMergeBranchMaps('Path/To/Git/repo2'),
                         {})

    def test_getGitImpPreHooks(self):
        self.assertEqual(
            self.cfg.getGitImpPreHooks('Path/To/Git/repository', 'master'),
            [['gitprehook', 'arg'], ['gitmasterprehook']])
        self.assertEqual(
            self.cfg.getGitImpPreHooks('Path/To/Git/repository', 'a1'),
            [['gitprehook', 'arg'], ['gita1prehook']])

    def test_getGitImpPostHooks(self):
        self.assertEqual(
            self.cfg.getGitImpPostHooks('Path/To/Git/repository', 'master'),
            [['gitposthook'], ['gitmasterposthook']])

    def test_getGitExpPreHooks(self):
        self.assertEqual(
            self.cfg.getGitExpPreHooks('Path/To/Git/repository', 'master'),
            [['gitprehook', 'arg'], ['gitmasterprehook']])
        self.assertEqual(
            self.cfg.getGitExpPreHooks('Path/To/Git/repository', 'a1'),
            [['gitprehook', 'arg'], ['gita1prehook']])

    def test_getGitExpPostHooks(self):
        self.assertEqual(
            self.cfg.getGitExpPostHooks('Path/To/Git/repository', 'master'),
            [['gitposthook'], ['gitmasterposthook']])

    def test_getCVSPreHooks(self):
        self.assertEqual(
            self.cfg.getCVSPreHooks('Path/To/Git/repository', 'cvs-a1'),
            [])
        self.assertEqual(
            self.cfg.getCVSPreHooks('Path/To/Git/repo2', 'cvs-a2'),
            [['cvsa2prehook', 'quoted arg']])

    def test_getCVSPostHooks(self):
        self.assertEqual(
            self.cfg.getCVSPostHooks('Path/To/Git/repository', 'cvs-a1'),
            [['cvsa1posthook']])

    def test_getEmail(self):
        self.assertEqual(self.cfg.getEmail('Path/To/Git/repository'),
                         ['foo@bar', 'baz@blah'])

    def test_getEmailDefault(self):
        cfg = repositorymap.RepositoryConfig(StringIO('''
[GLOBAL]
email = foo@bar
[repo]
        '''))
        self.assertEqual(cfg.getEmail('repo'), ['foo@bar'])

    def test_getEmailNone(self):
        self.assertEqual(self.cfg.getEmail('Path/To/Git/repo2'),
                         None)

    def test_duplicateRepositoryNameError(self):
        self.assertRaises(KeyError, repositorymap.RepositoryConfig, self.bad)

    def test_requireSkeletonAbsolutePaths(self):
        badcfg = StringIO('[foo]\nskeleton = baz\n')
        self.assertRaises(ValueError, repositorymap.RepositoryConfig, badcfg)
