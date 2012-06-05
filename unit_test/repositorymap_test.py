import ConfigParser
import os
from cStringIO import StringIO
import tempfile
import testutils

from gitcvs import repositorymap

class TestRepositoryConfig(testutils.TestCase):
    def setUp(self):
        self.fd, self.cf = tempfile.mkstemp(suffix='.gitcvs')
        file(self.cf, 'r+').write('''
[GLOBAL]
gitroot = git@host2
cvsroot = @server2:/path
[Path/To/Git/repository]
gitroot = git@host
cvsroot = @servername:/path
cvspath = Path/To/CVS/directory
skeleton = /path/to/skeleton
branchfrom = branchroot
cvs.a1 = a1
cvs.a2 = a2
git.master = a2
git.a1 = a1
prefix.a2 = cvs-a2-prefix
merge.cvs-a2 = a2 master
merge.cvs-a1 = a1
email = foo@bar baz@blah

[Path/To/Git/repo2]
cvspath = Path/To/CVS/directory
git.master = a2
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

    def test_getCVSRoot(self):
        self.assertEqual(self.cfg.getCVSRoot('Path/To/Git/repository', 'usr'),
                         ':pserver:usr@servername:/path')
    
    def test_getCVSRootDefault(self):
        self.assertEqual(self.cfg.getCVSRoot('Path/To/Git/repo2', 'usr'),
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

    def test_getMergeBranchMaps(self):
        self.assertEqual(self.cfg.getMergeBranchMaps('Path/To/Git/repository'),
                         {'cvs-a2': set(('a2', 'master')),
                          'cvs-a1': set(('a1',))})

    def test_getMergeBranchMapsEmpty(self):
        self.assertEqual(self.cfg.getMergeBranchMaps('Path/To/Git/repo2'),
                         {})

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
