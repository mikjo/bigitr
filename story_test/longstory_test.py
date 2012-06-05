from cStringIO import StringIO
import mock
import os
import tempfile
import unittest

from gitcvs import cvsimport, gitexport, context, git, cvs

class TestStory(unittest.TestCase):
    def setUp(self):
        self.oldcwd = os.getcwd()
        self.workdir = tempfile.mkdtemp(suffix='.gitcvs')
        # config directories
        self.logdir = self.workdir + '/log'
        os.makedirs(self.logdir)
        self.gitdir = self.workdir + '/git'
        os.makedirs(self.gitdir)
        self.cvsdir = self.workdir + '/cvs'
        os.makedirs(self.cvsdir)
        self.expdir = self.workdir + '/exp'
        os.makedirs(self.expdir)
        self.skeldir = self.workdir + '/skel'
        os.makedirs(self.skeldir + '/m2')
        file(self.skeldir + '/m2/.gitignore', 'w').write(
            '*.jar\n*.o\n.cvsignore\n')
        # outside the system: the "server" directories
        self.cvsroot = self.workdir + '/cvsroot'
        os.makedirs(self.cvsroot)
        self.gitroot = self.workdir + '/gitroot'
        os.makedirs(self.gitroot + '/git')
        # outside the system: the "checkout" directories
        self.cvsco = self.workdir + '/cvsco'
        os.makedirs(self.cvsco)
        self.gitco = self.workdir + '/gitco'
        os.makedirs(self.gitco)

        if 'CVSROOT' in os.environ:
            self.oldcvsroot = os.environ['CVSROOT']
        else:
            self.oldcvsroot = None
        os.unsetenv('CVSROOT')
        appConfig = StringIO('[global]\n'
                             'logdir = %s\n'
                             'gitdir = %s\n'
                             '[export]\n'
                             'cvsdir = %s\n'
                             '[import]\n'
                             'cvsdir = %s\n'
                             %(self.logdir,
                               self.gitdir,
                               self.cvsdir,
                               self.expdir) # "cvs export" to import into git
                            )
        repConfig = StringIO('[GLOBAL]'
                             'cvsroot = %s\n'
                             'gitroot = %s/\n'
                             '[git/module1]\n'
                             'cvspath = module1\n'
                             'cvs.b1 = b1\n'
                             'cvs.b2 = b2\n'
                             'git.master = b2\n'
                             'git.b1 = b1\n'
                             'prefix.b1 = SOME FIXED STRING\n'
                             '[git/module2]\n'
                             'cvspath = module2\n'
                             'skeleton = %s/m2\n'
                             'cvs.b1 = b1\n'
                             'git.master = b1\n'
                             '[git/module3]\n'
                             'cvspath = module3\n'
                             'cvs.b1 = b1\n'
                             'git.master = b1\n'
                             % (self.cvsroot,
                                self.gitroot,
                                self.skeldir)
                             )
        self.ctx = context.Context(appConfig, repConfig)
        self.getCVSRoot = self.ctx.getCVSRoot
        self.getGitRef = self.ctx.getGitRef
        self.ctx.getCVSRoot = mock.Mock()
        self.ctx.getCVSRoot.return_value = self.cvsroot
        self.ctx.getGitRef = lambda(a): '/'.join((self.gitroot, a))

    @staticmethod
    def removeRecursive(dir):
        for b, dirs, files in os.walk(dir, topdown=False):
            for f in files:
                os.remove('/'.join((b, f)))
            for d in dirs:
                os.rmdir('/'.join((b, d)))
        os.removedirs(dir)

    def tearDown(self):
        os.chdir(self.oldcwd)
        self.removeRecursive(self.workdir)
        if self.oldcvsroot:
            os.environ['CVSROOT'] = self.oldcvsroot
        else:
            os.unsetenv('CVSROOT')
        self.ctx.getCVSRoot = self.getCVSRoot
        self.ctx.getGitRef = self.getGitRef

    def unpack(self, tarball):
        os.system('tar -x -C %s -z -f %s/testdata/%s' %(
                  self.workdir,
                  os.environ['BASEDIR'],
                  tarball))

    def pack(self, tarball):
        tarball = '/'.join((os.environ['BASEDIR'], 'testdata', tarball))
        if not os.path.exists(tarball):
            # do not pack log (unnecessary) or git, cvsco (workdir changes)
            os.system('tar -c -C %s -z -f %s gitroot cvs cvsroot'
                      %(self.workdir, tarball))

    def test_lowlevel1(self):
        'test initial import process'
        self.unpack('TESTROOT.1.tar.gz')
        imp = cvsimport.Importer(self.ctx, 'johndoe')
        exp = gitexport.Exporter(self.ctx, 'johndoe')
        Git = git.Git(self.ctx, 'git/module1')
        CVS = cvs.CVS(self.ctx, 'git/module1', 'b1', imp.username)
        # the tool otherwise assumes that the remote repository exists
        os.system('git init --bare %s/git/module1' %self.gitroot)
        imp.importcvs('git/module1', Git, CVS, 'b1', 'cvs-b1')
        self.assertTrue(os.path.exists(self.gitdir + '/module1/1'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/2'))
        self.assertFalse(os.path.exists(self.gitdir + '/module1/3'))
        self.assertFalse(os.path.exists(self.gitdir + '/module1/.gitignore'))

        # now test with no changes in CVS
        imp.importcvs('git/module1', Git, CVS, 'b1', 'cvs-b1')
        self.assertTrue(os.path.exists(self.gitdir + '/module1/1'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/2'))
        self.assertFalse(os.path.exists(self.gitdir + '/module1/3'))

        os.system('cd %s; CVSROOT=%s cvs co -r b1 module1'
                  %(self.cvsco, self.cvsroot))
        file(self.cvsco + '/module1/3', 'w').write('3\n')
        os.system('cd %s/module1; cvs add 3; cvs commit -m "add 3"'
                  %self.cvsco)

        imp.importcvs('git/module1', Git, CVS, 'b1', 'cvs-b1')
        self.assertTrue(os.path.exists(self.gitdir + '/module1/1'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/2'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/3'))
        self.assertEqual(file(self.gitdir + '/module1/3').read(), '3\n')

        # now test with no changes in CVS
        imp.importcvs('git/module1', Git, CVS, 'b1', 'cvs-b1')
        self.assertTrue(os.path.exists(self.gitdir + '/module1/1'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/2'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/3'))
        self.assertEqual(file(self.gitdir + '/module1/3').read(), '3\n')

        os.system('cd %s/module1; cvs tag -b b2' %self.cvsco)
        file(self.cvsco + '/module1/4', 'w').write('4\n')
        os.system('cd %s/module1; cvs add 4; cvs commit -r b2 -m "add 4";'
                  'cvs up -r b2'
                  %self.cvsco)

        # make sure that the new CVS branch does not break the old one
        imp.importcvs('git/module1', Git, CVS, 'b1', 'cvs-b1')
        self.assertTrue(os.path.exists(self.gitdir + '/module1/1'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/2'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/3'))
        self.assertEqual(file(self.gitdir + '/module1/3').read(), '3\n')
        self.assertFalse(os.path.exists(self.gitdir + '/module1/4'))

        # new CVS branch requires separate CVS object that knows about it
        CVS2 = cvs.CVS(self.ctx, 'git/module1', 'b2', imp.username)
        imp.importcvs('git/module1', Git, CVS2, 'b2', 'cvs-b2')
        self.assertTrue(os.path.exists(self.gitdir + '/module1/1'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/2'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/3'))
        self.assertEqual(file(self.gitdir + '/module1/3').read(), '3\n')
        self.assertEqual(file(self.gitdir + '/module1/4').read(), '4\n')

        # test importing the removal of a file
        os.remove(self.cvsco + '/module1/3')
        os.system('cd %s/module1; cvs remove 3;'
                  ' cvs commit -m "removed 3 in b2"' %self.cvsco)
        imp.importcvs('git/module1', Git, CVS2, 'b2', 'cvs-b2')
        self.assertTrue(os.path.exists(self.gitdir + '/module1/1'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/2'))
        self.assertFalse(os.path.exists(self.gitdir + '/module1/3'))
        self.assertEqual(file(self.gitdir + '/module1/4').read(), '4\n')

        # make sure that removal on new CVS branch does not break the old one
        imp.importcvs('git/module1', Git, CVS, 'b1', 'cvs-b1')
        self.assertTrue(os.path.exists(self.gitdir + '/module1/1'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/2'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/3'))
        self.assertEqual(file(self.gitdir + '/module1/3').read(), '3\n')
        self.assertFalse(os.path.exists(self.gitdir + '/module1/4'))

        # and change branch again
        imp.importcvs('git/module1', Git, CVS2, 'b2', 'cvs-b2')
        self.assertTrue(os.path.exists(self.gitdir + '/module1/1'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/2'))
        self.assertFalse(os.path.exists(self.gitdir + '/module1/3'))
        self.assertEqual(file(self.gitdir + '/module1/4').read(), '4\n')

        # make sure that nothing conflicts with another module
        Gitm2 = git.Git(self.ctx, 'git/module2')
        CVSm2 = cvs.CVS(self.ctx, 'git/module2', 'b1', imp.username)
        # the tool otherwise assumes that the remote repository exists
        os.system('git init --bare %s/git/module2' %self.gitroot)
        imp.importcvs('git/module2', Gitm2, CVSm2, 'b1', 'cvs-b1')
        self.assertTrue(os.path.exists(self.gitdir + '/module2/1'))
        # ensure that files get cleaned up
        self.assertFalse(os.path.exists(self.gitdir + '/module2/bad.jar'))
        self.assertEqual(file(self.gitdir + '/module2/.gitignore').read(),
            '*.jar\n*.o\n.cvsignore\n')
        # .cvsignore file was ignored
        self.assertFalse(os.path.exists(self.gitdir + '/module2/.cvsignore'))

        # make sure that a stray file is cleaned up where necessary
        file('%s/module2/bad.jar' %self.gitdir, 'w')
        imp.importcvs('git/module2', Gitm2, CVSm2, 'b1', 'cvs-b1')
        self.assertFalse(os.path.exists(self.gitdir + '/module2/bad.jar'))

        # merge cvs-b1 onto master, including not having .cvsignore
        os.system('cd %s/module2; '
                  'git checkout master; '
                  'git merge cvs-b1 -m "prepare for export"; '
                  'git push origin master; '
                  %self.gitdir)

        # make sure that .cvsignore was not deleted from CVS when we export
        exp.exportgit('git/module2', Gitm2, CVSm2, 'master', 'export-master')
        self.assertTrue(os.path.exists(
            self.cvsdir + '/module2/b1/module2/.cvsignore'))
        self.assertTrue(os.path.exists(
            self.cvsdir + '/module2/b1/module2/ignore/.cvsignore'))
        # make sure that bad.jar WAS deleted from CVS when we exported
        self.assertFalse(os.path.exists(
            self.cvsdir + '/module2/b1/module2/bad.jar'))

        # .gitignore primed from .cvsignore if it exists and no skeleton
        Gitm3 = git.Git(self.ctx, 'git/module3')
        CVSm3 = cvs.CVS(self.ctx, 'git/module3', 'b1', imp.username)
        # the tool otherwise assumes that the remote repository exists
        os.system('git init --bare %s/git/module3' %self.gitroot)
        imp.importcvs('git/module3', Gitm3, CVSm3, 'b1', 'cvs-b1')
        os.system('cd %s/module3; '
                  'git checkout master; '
                  %self.gitdir)
        self.assertEqual(file(self.gitdir + '/module3/.gitignore').read(),
            'copy.to.gitignore\n')

        # Make sure that we don't accidentally delete a CVS branch
        self.assertRaises(RuntimeError, exp.exportBranches, 'git/module3', Gitm3)

        self.pack('TESTROOT.2.tar.gz')

    def test_lowlevel2(self):
        'test updating multiple branches in multiple repositories together'
        self.unpack('TESTROOT.2.tar.gz')
        imp = cvsimport.Importer(self.ctx, 'johndoe')
        Git = git.Git(self.ctx, 'git/module1')
        # set up work directory
        imp.importAll()

        # now make a bunch of changes, and ensure that they are all
        # imported by calling importAll once
        os.system('cd %s; CVSROOT=%s cvs co -r b1 module1'
                  %(self.cvsco, self.cvsroot))
        os.system('cd %s/module1; '
                  'cvs up -r b1; '
                  'touch b1.1; '
                  'cvs add b1.1; '
                  'cvs commit -r b1 -m "added b1.1 to b1"; '
                  'cvs up -r b2; '
                  'touch b2.1; '
                  'cvs add b2.1; '
                  'cvs commit -r b2 -m "added b2.1 to b2"; '
                  %self.cvsco)
        os.system('cd %s; CVSROOT=%s cvs co -r b1 module2'
                  %(self.cvsco, self.cvsroot))
        os.system('cd %s/module2; '
                  'touch 9; '
                  'cvs add 9 ; '
                  'cvs commit -m "added 9"; '
                  %self.cvsco)
        imp.importAll()
        self.assertTrue(os.path.exists(self.gitdir + '/module2/9'))
        os.system('cd %s/module1; git checkout cvs-b1' %self.gitdir)
        self.assertTrue(os.path.exists(self.gitdir + '/module1/b1.1'))
        self.assertFalse(os.path.exists(self.gitdir + '/module1/b2.1'))
        os.system('cd %s/module1; git checkout cvs-b2' %self.gitdir)
        self.assertFalse(os.path.exists(self.gitdir + '/module1/b1.1'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/b2.1'))
        self.pack('TESTROOT.3.tar.gz')

    def test_lowlevel3(self):
        'test imports onto merged branches'
        self.unpack('TESTROOT.3.tar.gz')
        imp = cvsimport.Importer(self.ctx, 'johndoe')
        Git = git.Git(self.ctx, 'git/module1')
        # set up work directory
        imp.importBranches('git/module1', Git)

        os.system('cd %s/module1; '
                  'git branch b1 cvs-b1; '
                  'git branch master cvs-b2; '
                  'git checkout master; '
                  'git merge b1 -s ours -m "setting start point for b1 merge"; '
                  'git push origin master; '
                  'git push origin b1; '
                  %self.gitdir)

        os.system('cd %s; CVSROOT=%s cvs co -r b1 module1'
                  %(self.cvsco, self.cvsroot))
        os.system('cd %s/module1; '
                  'cvs up -r b1; '
                  'touch b1.2; '
                  'cvs add b1.2; '
                  'cvs commit -r b1 -m "added b1.2 to b1"; '
                  'cvs up -r b2; '
                  'touch b2.2; '
                  'cvs add b2.2; '
                  'cvs commit -r b2 -m "added b2.2 to b2"; '
                  %self.cvsco)
        imp.importAll()
        os.system('cd %s/module1; git checkout cvs-b1' %self.gitdir)
        self.assertTrue(os.path.exists(self.gitdir + '/module1/b1.2'))
        self.assertFalse(os.path.exists(self.gitdir + '/module1/b2.2'))
        os.system('cd %s/module1; git checkout cvs-b2' %self.gitdir)
        self.assertFalse(os.path.exists(self.gitdir + '/module1/b1.2'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/b2.2'))

        os.system('cd %s/module1; '
                  'git checkout master; '
                  'git merge cvs-b2 -m "latest changes from cvs b2"; '
                  'git merge cvs-b1 -m "latest merge from cvs b1"; '
                  'git push origin master; '
                  %self.gitdir)
        self.assertTrue(os.path.exists(self.gitdir + '/module1/b1.2'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/b2.2'))
        self.assertFalse(os.path.exists(self.gitdir + '/module1/b1.1'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/b2.2'))

        self.pack('TESTROOT.4.tar.gz')

    def test_lowlevel4Junk(self):
        'test throwing away junk in the git directory'
        self.unpack('TESTROOT.4.tar.gz')
        imp = cvsimport.Importer(self.ctx, 'johndoe')
        Git = git.Git(self.ctx, 'git/module1')
        CVS = cvs.CVS(self.ctx, 'git/module1', 'b1', imp.username)
        # set up work directory
        imp.importcvs('git/module1', Git, CVS, 'b1', 'cvs-b1')
        file('%s/module1/transient' %self.gitdir, 'w')
        imp.importcvs('git/module1', Git, CVS, 'b1', 'cvs-b1')
        self.assertFalse(os.path.exists(self.gitdir + '/module1/transient'))
        # do not need to pack anything, since no changes have been made

    def test_lowlevel4BadGitBranch(self):
        'test error on specifying unknown git source branch'
        self.unpack('TESTROOT.4.tar.gz')
        exp = gitexport.Exporter(self.ctx, 'johndoe')
        Git = git.Git(self.ctx, 'git/module1')
        CVS = cvs.CVS(self.ctx, 'git/module1', 'b1', exp.username)
        self.assertRaises(KeyError, exp.exportgit,
            'git/module1', Git, CVS, 'wRoNgBrAnCh', 'export-yuck')
        # do not need to pack anything, since no changes have been made

    def test_lowlevel4(self):
        'test exporting git branch changes to cvs'
        self.unpack('TESTROOT.4.tar.gz')
        exp = gitexport.Exporter(self.ctx, 'johndoe')
        imp = cvsimport.Importer(self.ctx, 'johndoe')
        Git = git.Git(self.ctx, 'git/module1')
        CVSb1 = cvs.CVS(self.ctx, 'git/module1', 'b1', imp.username)
        CVSb2 = cvs.CVS(self.ctx, 'git/module1', 'b2', imp.username)
        # really need to work in a separate checkout to make sure that
        # we pull changes
        os.system('cd %s; git clone %s/git/module1' %(self.gitco, self.gitroot))
        os.system('cd %s/module1; '
                  'git checkout b1; '
                  'git merge origin/cvs-b1; '
                  'mkdir newdir; '
                  'git mv b1.2 newdir; '
                  'git commit -a -m "moved b1.2 to newdir"; '
                  'git push --all; '
                  %self.gitco)
        exp.exportgit('git/module1', Git, CVSb1, 'b1', 'export-b1')
        self.assertTrue('SOME FIXED STRING' in
                        file(self.cvsroot+'/module1/Attic/b1.2,v').read())
        imp.importcvs('git/module1', Git, CVSb1, 'b1', 'cvs-b1')
        os.system('cd %s/module1; '
                  'git fetch; '
                  'git merge origin/cvs-b1 -m "merge cvs-b1 to b1"; '
                  'git checkout master; '
                  'git merge b1 -m "merge cvs-b1 to master"; '
                  'git push --all; '
                  %self.gitco)
        exp.exportgit('git/module1', Git, CVSb2, 'master', 'export-master')
        os.system('cd %s/module1; '
                  'git fetch; '
                  'git checkout master; '
                  'touch added-on-git-master; '
                  'git add added-on-git-master; '
                  'git commit -m "add added-on-git-master"; '
                  'git push --all; '
                  %self.gitco)
        exp.exportgit('git/module1', Git, CVSb2, 'master', 'export-master')
        self.assertFalse('SOME FIXED STRING' in
                        file(self.cvsroot+'/module1/Attic/added-on-git-master,v').read())
        self.assertTrue('    add added-on-git-master' in
                        file(self.cvsroot+'/module1/Attic/added-on-git-master,v').read())
        imp.importcvs('git/module1', Git, CVSb2, 'b2', 'cvs-b2')
        os.system('cd %s/module1; '
                  'git fetch; '
                  'git checkout master; '
                  'git merge origin/cvs-b2 -m "merge cvs-b2 to master"; '
                  'git push --all; '
                  %self.gitco)
        exp.exportgit('git/module1', Git, CVSb2, 'master', 'export-master')
        self.pack('TESTROOT.5.tar.gz')

        os.chdir(self.gitdir + '/module1')
        # all branches with "master" in the name now point to the same hash:
        self.assertEqual(
            len(set([x[0] for x in Git.refs() if 'master' in x[1]])),
            1)


    def test_lowlevel5(self):
        'test automated merge'
        self.ctx._rm.set('git/module1', 'merge.cvs-b1', 'b1 b2')
        self.ctx._rm.set('git/module1', 'merge.cvs-b2', 'b2')
        self.ctx._rm.set('git/module1', 'merge.b2', 'master')
        # note: not merging b1 onto master on purpose for a test case
        # difference; in normal use, b1 would probably be merged onto master

        self.unpack('TESTROOT.5.tar.gz')
        exp = gitexport.Exporter(self.ctx, 'johndoe')
        imp = cvsimport.Importer(self.ctx, 'johndoe')
        Git = git.Git(self.ctx, 'git/module1')
        CVSb1 = cvs.CVS(self.ctx, 'git/module1', 'b1', imp.username)

        os.system('cd %s; git clone %s/git/module1' %(self.gitco, self.gitroot))
        os.system('cd %s/module1 && '
                  'git checkout cvs-b2 &&'
                  'git branch b2 && '
                  'git push origin b2; '
                  'git branch --set-upstream b2 origin/b2; '
                  %self.gitco)

        os.system('cd %s; CVSROOT=%s cvs co -r b1 module1'
                  %(self.cvsco, self.cvsroot))
        file(self.cvsco + '/module1/cascade', 'w').write('cascade\n')
        os.system('cd %s/module1; cvs add cascade; cvs commit -m "add cascade"'
                  %self.cvsco)

        imp.importcvs('git/module1', Git, CVSb1, 'b1', 'cvs-b1')

        for branch in ('cvs-b1', 'b1', 'b2', 'master'):
            # the workdir should not need a pull
            os.system('cd %s/module1; git checkout %s; '
                      %(self.gitdir, branch))
            self.assertEqual(file(self.gitdir + '/module1/cascade').read(),
                                  'cascade\n')
            # the user's checkout needs a pull but it should all be there
            os.system('cd %s/module1; git checkout %s; git pull'
                      %(self.gitco, branch))
            self.assertEqual(file(self.gitco + '/module1/cascade').read(),
                                  'cascade\n')

        # now create an import conflict on master
        file(self.cvsco + '/module1/cascade', 'w').write('please cascade\n')
        os.system('cd %s/module1; cvs add cascade; cvs commit -m "prep conflict"'
                  %self.cvsco)
        file(self.gitco + '/module1/cascade', 'w').write('do not cascade\n')
        os.system('cd %s/module1; git commit -a -m "create merge conflict" ;'
                  'git push origin master;'
                  %self.gitco)

        self.assertRaises(RuntimeError,
            imp.importcvs, 'git/module1', Git, CVSb1, 'b1', 'cvs-b1')
        os.system('cd %s/module1; git checkout master; git pull --all'
                  %self.gitco)

        # resolve conflict:
        file(self.gitco + '/module1/cascade', 'w').write('please cascade\n')
        os.system('cd %s/module1; git commit -a -m "resolve merge conflict" ;'
                  'git push origin master;'
                  %self.gitco)
        imp.importcvs('git/module1', Git, CVSb1, 'b1', 'cvs-b1')
        # and now make sure they were all pushed
        for branch in ('cvs-b1', 'b1', 'b2', 'master'):
            # the workdir should not need a pull
            os.system('cd %s/module1; git checkout %s; '
                      %(self.gitdir, branch))
            self.assertEqual(file(self.gitdir + '/module1/cascade').read(),
                                  'please cascade\n')
            # the user's checkout needs a pull but it should all be there
            os.system('cd %s/module1; git checkout %s; git pull'
                      %(self.gitco, branch))
            self.assertEqual(file(self.gitco + '/module1/cascade').read(),
                                  'please cascade\n')

        # we have not yet exported, so CVS's b2 and Git's cvs-b2 do
        # not have the cascade file at all yet
        os.system('cd %s/module1; git checkout cvs-b2; git pull' %self.gitco)
        self.assertFalse(os.path.exists(self.gitco + '/module1/cascade'))

        os.system('cd %s/module1; cvs up -r b2 ' %self.cvsco)
        self.assertFalse(os.path.exists(self.cvsco + '/module1/cascade'))

        # now push all of this back to CVS
        exp.exportBranches('git/module1', Git)

        os.system('cd %s/module1; cvs up -r b2 ' %self.cvsco)
        self.assertEqual(file(self.cvsco + '/module1/cascade').read(),
                              'please cascade\n')

        # and check that the import picks up the merge to the cvs-b2 branch
        imp.importBranches('git/module1', Git)
        os.system('cd %s/module1; git checkout cvs-b2; git pull' %self.gitco)
        self.assertEqual(file(self.gitco + '/module1/cascade').read(),
                              'please cascade\n')

        self.pack('TESTROOT.6.tar.gz')

    def test_lowlevel5keyword(self):
        'test cvs keyword demangling'
        self.unpack('TESTROOT.5.tar.gz')
        exp = gitexport.Exporter(self.ctx, 'johndoe')
        imp = cvsimport.Importer(self.ctx, 'johndoe')
        Git = git.Git(self.ctx, 'git/module1')
        CVSb1 = cvs.CVS(self.ctx, 'git/module1', 'b1', imp.username)
        CVSb2 = cvs.CVS(self.ctx, 'git/module1', 'b2', imp.username)
        os.system('cd %s; CVSROOT=%s cvs co -r b1 module1'
                  %(self.cvsco, self.cvsroot))
        file(self.cvsco + '/module1/keywords', 'w').write('''
            $Author$
            $Date$
            $Header$
            $Id$
            $Name$
            $Locker$
            $RCSfile$
            $Revision$
            $Source$
            $State$
            $Log$
''')
        os.system('cd %s/module1; '
                  'cvs add keywords; '
                  'cvs commit -m "add keywords"'
                  %self.cvsco)
        keywords = file(self.cvsco + '/module1/keywords').read()
        self.assertTrue('$Author:' in keywords)
        self.assertTrue('$Date:' in keywords)
        self.assertTrue('$Header:' in keywords)
        self.assertTrue('$Id:' in keywords)
        self.assertTrue('$Name:' in keywords)
        self.assertTrue('$Locker:' in keywords)
        self.assertTrue('$RCSfile:' in keywords)
        self.assertTrue('$Revision:' in keywords)
        self.assertTrue('$Source:' in keywords)
        self.assertTrue('$State:' in keywords)
        self.assertTrue('$Log:' in keywords)
        imp.importcvs('git/module1', Git, CVSb1, 'b1', 'cvs-b1')
        keywords = file(self.gitdir + '/module1/keywords').read()
        self.assertTrue('$Author$' in keywords)
        self.assertTrue('$Date$' in keywords)
        self.assertTrue('$Header$' in keywords)
        self.assertTrue('$Id$' in keywords)
        self.assertTrue('$Name$' in keywords)
        self.assertTrue('$Locker$' in keywords)
        self.assertTrue('$RCSfile$' in keywords)
        self.assertTrue('$Revision$' in keywords)
        self.assertTrue('$Source$' in keywords)
        self.assertTrue('$State$' in keywords)
        self.assertTrue('$Log:' not in keywords)
        self.assertTrue('OldLog:' in keywords)
