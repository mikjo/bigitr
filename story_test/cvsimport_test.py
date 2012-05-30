from cStringIO import StringIO
import mock
import os
import tempfile
import unittest

from gitcvs import cvsimport, context, git, cvs

class TestCVSImportStory(unittest.TestCase):
    def setUp(self):
        # for config
        self.logdir = tempfile.mkdtemp(suffix='.log.gitcvs')
        self.gitdir = tempfile.mkdtemp(suffix='.git.gitcvs')
        self.cvsdir = tempfile.mkdtemp(suffix='.cvs.gitcvs')
        self.cvsroot = tempfile.mkdtemp(suffix='.cvsroot.gitcvs')
        # outside the system
        self.gitroot = tempfile.mkdtemp(suffix='.gitroot.gitcvs')
        self.cvsco = tempfile.mkdtemp(suffix='.cvsco.gitcvs')
        os.mkdir(self.gitroot + '/git')
        os.system('tar -x -C %s -z -f %s/testdata/CVSROOT.1.tar.gz' %(
                  self.cvsroot, os.environ['BASEDIR']))
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
                             %(self.logdir,
                               self.gitdir,
                               self.cvsdir)
                            )
        repConfig = StringIO('[GLOBAL]'
                             'cvsroot = %s\n'
                             'gitroot = %s/\n'
                             '[git/module1]\n'
                             'cvspath = module1\n'
                             'cvs.b1 = b1\n'
                             'git.b2 = b2\n'
                             '[git/module2]\n'
                             'cvspath = module2\n'
                             % (self.cvsroot,
                                self.gitroot)
                             )
        self.ctx = context.Context(appConfig, repConfig)
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
        self.removeRecursive(self.logdir)
        self.removeRecursive(self.gitdir)
        self.removeRecursive(self.cvsdir)
        self.removeRecursive(self.cvsroot)
        self.removeRecursive(self.gitroot)
        self.removeRecursive(self.cvsco)
        if self.oldcvsroot:
            os.environ['CVSROOT'] = self.oldcvsroot
        else:
            os.unsetenv('CVSROOT')

    def test_lowlevel(self):
        imp = cvsimport.Importer(self.ctx, 'johndoe')
        Git = git.Git(self.ctx, 'git/module1')
        CVS = cvs.CVS(self.ctx, 'git/module1', 'b1', imp.username)
        # the tool otherwise assumes that the remote repository exists
        os.system('git init --bare %s/git/module1' %self.gitroot)
        imp.importcvs('git/module1', Git, CVS, 'b1', 'cvs-b1')
        self.assertTrue(os.path.exists(self.gitdir + '/module1/1'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/2'))
        self.assertFalse(os.path.exists(self.gitdir + '/module1/3'))

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
