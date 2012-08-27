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

from cStringIO import StringIO
import mock
import os
import tempfile
import unittest

import bigitr
from bigitr import cvsimport, gitexport, context, git, cvs, util


class WorkDir(unittest.TestCase):
    def setUp(self):
        self.oldcwd = os.getcwd()
        self.workdir = tempfile.mkdtemp(suffix='.bigitr')
        # make sure that bad tests don't cause git commits in
        # the source repository!
        os.chdir(self.workdir)
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
        file(self.skeldir + '/m2/.gitattributes', 'w').write(
            '* text\n')
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

        self.oldenviron = {}
        self.unsetenv('CVSROOT')

        self.appConfigText = ('[global]\n'
                              'logdir = %s\n'
                              'gitdir = %s\n'
                              'compresslogs = false\n'
                              '[export]\n'
                              'cvsdir = %s\n'
                              '[import]\n'
                              'cvsdir = %s\n'
                              %(self.logdir,
                                self.gitdir,
                                self.cvsdir,
                                self.expdir) # "cvs export" to import into git
                              )
        self.repConfigText = ('[GLOBAL]\n'
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
    def tearDown(self):
        os.chdir(self.oldcwd)
        util.removeRecursive(self.workdir)
        for key, value in self.oldenviron.items():
            if value:
                os.environ[key] = value
            else:
                os.unsetenv(key)

    def savevar(self, var):
        if var in os.environ:
            self.oldenviron[var] = os.environ[var]
        else:
            self.oldenviron[var] = None

    def unsetenv(self, var):
        self.savevar(var)
        os.unsetenv(var)

    def setenv(self, var, value):
        self.savevar(var)
        os.environ[var] = value

    def unpack(self, tarball):
        os.system('tar -x -C %s -z -f %s/testdata/%s' %(
                  self.workdir,
                  os.environ['BASEDIR'],
                  tarball))

    def pack(self, tarball):
        tarball = '/'.join((os.environ['BASEDIR'], 'testdata', tarball))
        if not os.path.exists(tarball):
            # do not pack log (unnecessary) or git, cvsco (workdir changes)
            # do not pack cvs because it references transient CVSROOT
            os.system('tar -c -C %s -z -f %s gitroot cvsroot'
                      %(self.workdir, tarball))

    def assertNoTracebackLogs(self):
        for b, dirs, files in os.walk(self.logdir, topdown=False):
            for f in files:
                if f.endswith('.err'):
                    self.assertFalse('Traceback' in file('/'.join((b,f))).read())


class TestStoryAPI(WorkDir):
    def setUp(self):
        WorkDir.setUp(self)
        appConfig = StringIO(self.appConfigText)
        repConfig = StringIO(self.repConfigText)
        self.ctx = context.Context(appConfig, repConfig)

    def test_lowlevel1(self):
        'test initial import process'
        self.unpack('TESTROOT.1.tar.gz')
        imp = cvsimport.Importer(self.ctx)
        exp = gitexport.Exporter(self.ctx)
        Git = git.Git(self.ctx, 'git/module1')
        CVS = cvs.CVS(self.ctx, 'git/module1', 'b1')
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
        CVS2 = cvs.CVS(self.ctx, 'git/module1', 'b2')
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
        CVSm2 = cvs.CVS(self.ctx, 'git/module2', 'b1')
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
        # make sure that .gitignore and .gitattributes were not copied to CVS
        self.assertFalse(os.path.exists(
            self.cvsdir + '/module2/b1/module2/.gitignore'))
        self.assertFalse(os.path.exists(
            self.cvsdir + '/module2/b1/module2/.gitattributes'))

        # .gitignore primed from .cvsignore if it exists and no skeleton
        Gitm3 = git.Git(self.ctx, 'git/module3')
        CVSm3 = cvs.CVS(self.ctx, 'git/module3', 'b1')
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

        # The traceback and the exception are logged, and no blank lines
        self.assertEqual(
            [x.strip() for x in file(Gitm3.log.thiserr).readlines()
             if 'RuntimeError' in x or 'Traceback' in x or x == '\n'],
            ['Traceback (most recent call last):',
             "RuntimeError: Not committing empty branch 'b1' from git branch 'master'"])

        self.pack('TESTROOT.2.tar.gz')

    def test_lowlevel2badCVSBranch(self):
        # Make sure that we raise an error for missing CVS branch
        # and don't create a Git branch for it
        self.unpack('TESTROOT.2.tar.gz')
        imp = cvsimport.Importer(self.ctx)
        Git = git.Git(self.ctx, 'git/module1')
        CVSbad = cvs.CVS(self.ctx, 'git/module1', 'bad')
        self.assertRaises(ValueError, imp.importcvs,
            'git/module1', Git, CVSbad, 'bad', 'cvs-bad')
        # ensure that we didn't get to checking out a git dir,
        # let alone create a git branch
        self.assertFalse(os.path.exists(self.gitdir + '/module1'))

        os.system('cd %s; CVSROOT=%s cvs co -r b1 module1'
                  %(self.cvsco, self.cvsroot))
        os.system('cd %s/module1; '
                  'mkdir empty; '
                  'touch empty/bad; '
                  'cvs add empty; '
                  'cvs add empty/bad; '
                  'cvs commit -r b1 -m "add empty/bad to b1"; '
                  'cvs tag -b bad; '
                  'cvs update -r b1; '
                  'rm empty/bad; '
                  'cvs rm empty/bad; '
                  'cvs commit -r bad -m "remove empty/bad from bad"; '
                  %self.cvsco)

        self.ctx._rm.set('git/module1', 'cvspath', 'module1/empty')
        CVSbad = cvs.CVS(self.ctx, 'git/module1', 'bad')
        self.assertRaises(RuntimeError, imp.importcvs,
            'git/module1', Git, CVSbad, 'bad', 'cvs-bad')
        # ensure that we didn't get to checking out a git dir,
        # let alone create a git branch
        self.assertFalse(os.path.exists(self.gitdir + '/module1'))
        # do not pack anything, since we do not want to preseve these changes

    def test_lowlevel2(self):
        'test updating multiple branches in multiple repositories together'
        self.unpack('TESTROOT.2.tar.gz')
        imp = cvsimport.Importer(self.ctx)
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
        imp = cvsimport.Importer(self.ctx)
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
        imp = cvsimport.Importer(self.ctx)
        Git = git.Git(self.ctx, 'git/module1')
        CVS = cvs.CVS(self.ctx, 'git/module1', 'b1')
        # set up work directory
        imp.importcvs('git/module1', Git, CVS, 'b1', 'cvs-b1')
        file('%s/module1/transient' %self.gitdir, 'w')
        imp.importcvs('git/module1', Git, CVS, 'b1', 'cvs-b1')
        self.assertFalse(os.path.exists(self.gitdir + '/module1/transient'))
        # do not need to pack anything, since no changes have been made

    def test_lowlevel4BadGitBranch(self):
        'test error on specifying unknown git source branch'
        self.unpack('TESTROOT.4.tar.gz')
        exp = gitexport.Exporter(self.ctx)
        Git = git.Git(self.ctx, 'git/module1')
        CVS = cvs.CVS(self.ctx, 'git/module1', 'b1')
        self.assertRaises(KeyError, exp.exportgit,
            'git/module1', Git, CVS, 'wRoNgBrAnCh', 'export-yuck')
        # do not need to pack anything, since no changes have been made

    def test_lowlevel4(self):
        'test exporting git branch changes to cvs'
        self.unpack('TESTROOT.4.tar.gz')
        exp = gitexport.Exporter(self.ctx)
        imp = cvsimport.Importer(self.ctx)
        Git = git.Git(self.ctx, 'git/module1')
        CVSb1 = cvs.CVS(self.ctx, 'git/module1', 'b1')
        CVSb2 = cvs.CVS(self.ctx, 'git/module1', 'b2')
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

        # test scripts firing correctly on merge
        scriptdir = self.workdir + '/script'
        os.makedirs(scriptdir)
        file(scriptdir + '/gitpost', 'w').write('\n'.join((
            '#!/bin/sh',
            r"git branch | grep '^\*' | sed 's/.*/BRANCHES: \0/g'"
            '',
        )))
        os.chmod(scriptdir + '/gitpost', 0755)
        self.ctx._rm.set('GLOBAL', 'posthook.git', scriptdir+'/gitpost')

        self.unpack('TESTROOT.5.tar.gz')
        exp = gitexport.Exporter(self.ctx)
        imp = cvsimport.Importer(self.ctx)
        Git = git.Git(self.ctx, 'git/module1')
        CVSb1 = cvs.CVS(self.ctx, 'git/module1', 'b1')

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

        # Test that the git hook always fired all the times it should have for merge
        self.assertEqual(
            [x.strip() for x in file(Git.log.thislog).readlines()
             if x.startswith('BRANCHES:')],
            ['BRANCHES: * cvs-b1',
             'BRANCHES: * b1',
             'BRANCHES: * b2',
             'BRANCHES: * master',
             'BRANCHES: * cvs-b1',
             'BRANCHES: * b1',
             'BRANCHES: * b2',
             'BRANCHES: * b1',
             'BRANCHES: * b2',
             'BRANCHES: * master',
             'BRANCHES: * b1',
             'BRANCHES: * master',
             'BRANCHES: * b1',
             'BRANCHES: * b2',
             'BRANCHES: * master',
             'BRANCHES: * cvs-b2',
             'BRANCHES: * b2',
             'BRANCHES: * master'])

        self.pack('TESTROOT.6.tar.gz')

    def test_lowlevel5keyword(self):
        'test cvs keyword demangling'
        self.unpack('TESTROOT.5.tar.gz')
        exp = gitexport.Exporter(self.ctx)
        imp = cvsimport.Importer(self.ctx)
        Git = git.Git(self.ctx, 'git/module1')
        CVSb1 = cvs.CVS(self.ctx, 'git/module1', 'b1')
        CVSb2 = cvs.CVS(self.ctx, 'git/module1', 'b2')
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
        # we need to add a new file in Git after the checkout is created
        # in CVS, to test the -kk option to cvs add...
        os.system('cd %s; git clone %s/git/module1' %(self.gitco, self.gitroot))
        os.system('cd %s/module1; '
                  'git checkout b1; '
                  "echo '$Id$' > k2; "
                  'git add k2; '
                  'git commit -a -m "add k2"; '
                  'git push --all; '
                  %self.gitco)
        exp.exportBranches('git/module1', Git)
        entries = file(self.cvsdir + '/module1/b1/module1/CVS/Entries'
            ).readlines()
        self.assertTrue([x for x in entries if 'k2' in x and '-kk' in x])
        kw1 = file(self.cvsroot+'/module1/Attic/k2,v').read()
        exp.exportBranches('git/module1', Git)
        kw2 = file(self.cvsroot+'/module1/Attic/k2,v').read()
        self.assertEqual(kw1, kw2)

    def test_lowlevel6lineEndingChangeWithCVSImport(self):
        'test converting line endings only does not break cvs import'
        self.unpack('TESTROOT.6.tar.gz')

        exp = gitexport.Exporter(self.ctx)
        imp = cvsimport.Importer(self.ctx)
        Git = git.Git(self.ctx, 'git/module1')
        CVSb1 = cvs.CVS(self.ctx, 'git/module1', 'b1')

        os.system('cd %s; CVSROOT=%s cvs co -r b1 module1'
                  %(self.cvsco, self.cvsroot))
        file(self.cvsco + '/module1/newline', 'w').write('a\r\nb\r\n')
        os.system('cd %s/module1; '
                  'cvs add -ko newline; '
                  'cvs commit -m "add newline"'
                  %self.cvsco)

        os.system('cd %s; git clone %s/git/module1' %(self.gitco, self.gitroot))
        os.system('cd %s/module1; '
                  'git checkout cvs-b1; '
                  "echo 'newline binary' > .gitattributes; "
                  'git add .gitattributes; '
                  'git commit -a -m "change .gitattributes"; '
                  'git push --all; '
                  %self.gitco)
        newline = file(self.cvsroot+'/module1/Attic/newline,v').read()
        # there should only be two \r\n's in the ,v file
        self.assertEqual(len(newline.split('\r\n')), 3)
        imp.importcvs('git/module1', Git, CVSb1, 'b1', 'cvs-b1')
        # the carriage returns should have been preserved
        self.assertEqual(os.stat(self.gitdir+'/module1/newline').st_size, 6)
        os.system('cd %s/module1; '
                  'git pull; '
                  "echo 'newline text=auto' > .gitattributes; "
                  'rm .git/index; '
                  'git reset; '
                  'git add -u; '
                  'git add .gitattributes; '
                  'git commit -a -m "add .gitattributes"; '
                  'git push --all; '
                  %self.gitco)
        imp.importcvs('git/module1', Git, CVSb1, 'b1', 'cvs-b1')
        file(self.cvsco + '/module1/newline', 'w').write('a\nb\n')
        os.system('cd %s/module1; '
                  'cvs commit -m "change newline"'
                  %self.cvsco)
        imp.importcvs('git/module1', Git, CVSb1, 'b1', 'cvs-b1')
        self.assertEqual(os.stat(self.gitdir+'/module1/newline').st_size, 4)

    def test_lowlevel6lineEndingChangeByHookNormalization(self):
        'test converting line endings by hooks that normalize'
        self.unpack('TESTROOT.6.tar.gz')

        scriptdir = self.workdir + '/script'
        os.makedirs(scriptdir)
        file(scriptdir + '/crnl', 'w').write('\n'.join((
            '#!/bin/sh -x',
            r"sed -i -r 's/\r//' newline",
            '',
        )))
        os.chmod(scriptdir + '/crnl', 0755)

        self.ctx._rm.set('git/module1', 'prehook.git.cvs-b1', scriptdir+'/crnl')
        self.ctx._rm.set('git/module1', 'prehook.cvs.b2', scriptdir+'/crnl')

        exp = gitexport.Exporter(self.ctx)
        imp = cvsimport.Importer(self.ctx)
        Git = git.Git(self.ctx, 'git/module1')
        CVSb1 = cvs.CVS(self.ctx, 'git/module1', 'b1')
        CVSb2 = cvs.CVS(self.ctx, 'git/module1', 'b2')

        os.system('cd %s; CVSROOT=%s cvs co -r b1 module1'
                  %(self.cvsco, self.cvsroot))
        file(self.cvsco + '/module1/newline', 'w').write('a\r\nb\r\n')
        os.system('cd %s/module1; '
                  'cvs add -ko newline; '
                  'cvs commit -m "add newline"'
                  %self.cvsco)

        newline = file(self.cvsroot+'/module1/Attic/newline,v').read()
        # there should only be two \r\n's in the ,v file
        self.assertEqual(len(newline.split('\r\n')), 3)
        imp.importcvs('git/module1', Git, CVSb1, 'b1', 'cvs-b1')
        # the hook should have normalized the newlines
        self.assertEqual(os.stat(self.gitdir+'/module1/newline').st_size, 4)

        os.system('cd %s; git clone %s/git/module1' %(self.gitco, self.gitroot))
        file(self.gitco + '/module1/newline', 'w').write('a\r\nb\r\n')
        os.system('cd %s/module1; '
                  'git checkout master; '
                  "echo 'newline binary' > .gitattributes; "
                  'git add .gitattributes newline; '
                  'git commit -a -m "change .gitattributes"; '
                  'git push --all; '
                  %self.gitco)
        self.assertEqual(os.stat(self.gitco+'/module1/newline').st_size, 6)

        exp.exportgit('git/module1', Git, CVSb2, 'master', 'export-master')
        self.assertEqual(os.stat(self.cvsdir+'/module1/b2/module1/newline').st_size, 4)

    def test_lowlevel6RunAllHookTypes(self):
        'test running all the types of hooks'
        self.unpack('TESTROOT.6.tar.gz')

        scriptdir = self.workdir + '/script'
        os.makedirs(scriptdir)

        file(scriptdir + '/gitpre', 'w').write('\n'.join((
            '#!/bin/sh',
            r"git branch | grep '^\*' | sed 's/.*/CMP PREBRANCHES: \0/g'"
            '',
        )))
        os.chmod(scriptdir + '/gitpre', 0755)

        file(scriptdir + '/gitpost', 'w').write('\n'.join((
            '#!/bin/sh',
            r"git branch | grep '^\*' | sed 's/.*/CMP POSTBRANCHES: \0/g'"
            '',
        )))
        os.chmod(scriptdir + '/gitpost', 0755)

        file(scriptdir + '/cvspre', 'w').write('\n'.join((
            '#!/bin/sh',
            'echo "CMP CVSPRE: ${PWD}"'
            '',
        )))
        os.chmod(scriptdir + '/cvspre', 0755)
        file(scriptdir + '/cvspost', 'w').write('\n'.join((
            '#!/bin/sh',
            'echo "CMP CVSPOST: ${PWD}"'
            '',
        )))
        os.chmod(scriptdir + '/cvspost', 0755)

        self.ctx._rm.set('GLOBAL', 'prehook.git', scriptdir+'/gitpre')
        self.ctx._rm.set('GLOBAL', 'prehook.cvs', scriptdir+'/cvspre')
        self.ctx._rm.set('GLOBAL', 'posthook.git', scriptdir+'/gitpost')
        self.ctx._rm.set('GLOBAL', 'posthook.cvs', scriptdir+'/cvspost')

        exp = gitexport.Exporter(self.ctx)
        imp = cvsimport.Importer(self.ctx)
        Git = git.Git(self.ctx, 'git/module1')
        CVSb1 = cvs.CVS(self.ctx, 'git/module1', 'b1')
        CVSb2 = cvs.CVS(self.ctx, 'git/module1', 'b2')

        os.system('cd %s; CVSROOT=%s cvs co -r b1 module1'
                  %(self.cvsco, self.cvsroot))
        file(self.cvsco + '/module1/trigger', 'w').write('trigger')
        os.system('cd %s/module1; '
                  'cvs add trigger; '
                  'cvs commit -m "add trigger"'
                  %self.cvsco)

        imp.importcvs('git/module1', Git, CVSb1, 'b1', 'cvs-b1')

        os.system('cd %s; git clone %s/git/module1' %(self.gitco, self.gitroot))
        os.system('cd %s/module1; '
                  'git checkout master; '
                  'echo trigger > trigger; '
                  'git add trigger; '
                  'git commit -a -m "add trigger"; '
                  'git push --all; '
                  %self.gitco)

        exp.exportgit('git/module1', Git, CVSb2, 'master', 'export-master')

        self.assertEqual(
            [x.strip() for x in file(Git.log.thislog).readlines()
             if x.startswith('CMP ')],
            ['CMP PREBRANCHES: * cvs-b1',
             'CMP POSTBRANCHES: * cvs-b1',
             'CMP PREBRANCHES: * master',
             'CMP CVSPRE: %s/module1/b2/module1' % self.cvsdir,
             'CMP CVSPOST: %s/module1/b2/module1' % self.cvsdir,
             'CMP POSTBRANCHES: * master'])

    def test_lowlevel6(self):
        'test exporting git branch changes to cvs with nested new subdirs'
        self.unpack('TESTROOT.6.tar.gz')
        exp = gitexport.Exporter(self.ctx)
        imp = cvsimport.Importer(self.ctx)
        Git = git.Git(self.ctx, 'git/module1')
        CVSb1 = cvs.CVS(self.ctx, 'git/module1', 'b1')

        # really need to work in a separate checkout to make sure that
        # we pull changes
        os.system('cd %s; git clone %s/git/module1' %(self.gitco, self.gitroot))
        os.system('cd %s/module1; '
                  'git checkout b1; '
                  'mkdir -p new/directory/tree; '
                  'echo content > new/directory/tree/file; '
                  'git add new; '
                  'git commit -a -m "add new/directory/tree/file"; '
                  'git push --all; '
                  %self.gitco)
        exp.exportgit('git/module1', Git, CVSb1, 'b1', 'export-b1')
        self.assertTrue('content' in
            file(self.cvsroot+'/module1/new/directory/tree/Attic/file,v').read())




class TestStoryCommands(WorkDir):
    def setUp(self):
        WorkDir.setUp(self)
        self.bindir = os.path.dirname(os.path.dirname(__file__)) + '/bin'
        self.exe = self.bindir + '/bigitr'
        self.cfgdir = self.workdir + '/cfg'
        os.makedirs(self.cfgdir)
        self.appCfgname = self.cfgdir + '/appcfg'
        file(self.appCfgname, 'w').write(self.appConfigText)
        self.setenv('BIGITR_APP_CONFIG', self.appCfgname)
        self.repCfgname = self.cfgdir + '/repcfg'
        file(self.repCfgname, 'w').write(self.repConfigText)
        self.setenv('BIGITR_REPO_CONFIG', self.repCfgname)

    def invoke(self, *args):
        self.assertRaises(SystemExit, bigitr.main, args)

    def test_import(self):
        'basic workflow from command invocation'
        # starts with same changes as low-level API version
        self.unpack('TESTROOT.1.tar.gz')
        # the tool otherwise assumes that the remote repository exists
        os.system('git init --bare %s/git/module1' %self.gitroot)
        cwd1 = os.getcwd()
        self.invoke('import', 'module1::b1')
        cwd2 = os.getcwd()
        self.assertEqual(cwd1, cwd2)
        self.assertTrue(os.path.exists(self.gitdir + '/module1/1'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/2'))
        self.assertFalse(os.path.exists(self.gitdir + '/module1/3'))
        self.assertFalse(os.path.exists(self.gitdir + '/module1/.gitignore'))

        # now test with no changes in CVS
        self.invoke('import', 'module1::b1')
        self.assertTrue(os.path.exists(self.gitdir + '/module1/1'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/2'))
        self.assertFalse(os.path.exists(self.gitdir + '/module1/3'))

        os.system('cd %s; CVSROOT=%s cvs co -r b1 module1'
                  %(self.cvsco, self.cvsroot))
        file(self.cvsco + '/module1/3', 'w').write('3\n')
        os.system('cd %s/module1; cvs add 3; cvs commit -m "add 3"'
                  %self.cvsco)

        self.invoke('import', 'module1::b1')
        self.assertTrue(os.path.exists(self.gitdir + '/module1/1'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/2'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/3'))
        self.assertEqual(file(self.gitdir + '/module1/3').read(), '3\n')

        # now test with no changes in CVS
        self.invoke('import', 'module1::b1')
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
        self.invoke('import', 'module1::b1')
        self.assertTrue(os.path.exists(self.gitdir + '/module1/1'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/1'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/2'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/3'))
        self.assertEqual(file(self.gitdir + '/module1/3').read(), '3\n')
        self.assertFalse(os.path.exists(self.gitdir + '/module1/4'))

        # new CVS branch requires separate CVS object that knows about it
        self.invoke('import', 'module1::b2')
        self.assertTrue(os.path.exists(self.gitdir + '/module1/1'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/2'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/3'))
        self.assertEqual(file(self.gitdir + '/module1/3').read(), '3\n')
        self.assertEqual(file(self.gitdir + '/module1/4').read(), '4\n')

        # test importing the removal of a file
        os.remove(self.cvsco + '/module1/3')
        os.system('cd %s/module1; cvs remove 3;'
                  ' cvs commit -m "removed 3 in b2"' %self.cvsco)
        self.invoke('import', 'module1::b2')
        self.assertTrue(os.path.exists(self.gitdir + '/module1/1'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/2'))
        self.assertFalse(os.path.exists(self.gitdir + '/module1/3'))
        self.assertEqual(file(self.gitdir + '/module1/4').read(), '4\n')

        # make sure that removal on new CVS branch does not break the old one
        self.invoke('import', 'module1::b1')
        self.assertTrue(os.path.exists(self.gitdir + '/module1/1'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/2'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/3'))
        self.assertEqual(file(self.gitdir + '/module1/3').read(), '3\n')
        self.assertFalse(os.path.exists(self.gitdir + '/module1/4'))

        # and change branch again
        self.invoke('import', 'module1::b2')
        self.assertTrue(os.path.exists(self.gitdir + '/module1/1'))
        self.assertTrue(os.path.exists(self.gitdir + '/module1/2'))
        self.assertFalse(os.path.exists(self.gitdir + '/module1/3'))
        self.assertEqual(file(self.gitdir + '/module1/4').read(), '4\n')

        # make sure that nothing conflicts with another module
        # the tool otherwise assumes that the remote repository exists
        os.system('git init --bare %s/git/module2' %self.gitroot)
        self.invoke('import', 'git/module2::b1')
        self.assertTrue(os.path.exists(self.gitdir + '/module2/1'))
        # ensure that files get cleaned up
        self.assertFalse(os.path.exists(self.gitdir + '/module2/bad.jar'))
        self.assertEqual(file(self.gitdir + '/module2/.gitignore').read(),
            '*.jar\n*.o\n.cvsignore\n')
        # .cvsignore file was ignored
        self.assertFalse(os.path.exists(self.gitdir + '/module2/.cvsignore'))

        # make sure that a stray file is cleaned up where necessary
        file('%s/module2/bad.jar' %self.gitdir, 'w')
        self.invoke('import', 'module2::b1')
        self.assertFalse(os.path.exists(self.gitdir + '/module2/bad.jar'))

        # merge cvs-b1 onto master, including not having .cvsignore
        os.system('cd %s/module2; '
                  'git checkout master; '
                  'git merge cvs-b1 -m "prepare for export"; '
                  'git push origin master; '
                  %self.gitdir)

        # make sure that .cvsignore was not deleted from CVS when we export
        self.invoke('export', 'module2::master')
        self.assertTrue(os.path.exists(
            self.cvsdir + '/module2/b1/module2/.cvsignore'))
        self.assertTrue(os.path.exists(
            self.cvsdir + '/module2/b1/module2/ignore/.cvsignore'))
        # make sure that bad.jar WAS deleted from CVS when we exported
        self.assertFalse(os.path.exists(
            self.cvsdir + '/module2/b1/module2/bad.jar'))
        # make sure that .gitignore and .gitattributes were not copied to CVS
        self.assertFalse(os.path.exists(
            self.cvsdir + '/module2/b1/module2/.gitignore'))
        self.assertFalse(os.path.exists(
            self.cvsdir + '/module2/b1/module2/.gitattributes'))

        # .gitignore primed from .cvsignore if it exists and no skeleton
        # the tool otherwise assumes that the remote repository exists
        os.system('git init --bare %s/git/module3' %self.gitroot)
        self.invoke('import', 'git/module3::b1')
        os.system('cd %s/module3; '
                  'git checkout master; '
                  %self.gitdir)
        self.assertEqual(file(self.gitdir + '/module3/.gitignore').read(),
            'copy.to.gitignore\n')
        self.assertNoTracebackLogs()

    def test_other_commands(self):
        self.unpack('TESTROOT.5.tar.gz')
        # create missing branch
        os.system('cd %s; git clone %s/git/module1' %(self.gitco, self.gitroot))
        os.system('cd %s/module1 && '
                  'git checkout cvs-b2 &&'
                  'git branch b2 && '
                  'git push origin b2; '
                  'git branch --set-upstream b2 origin/b2; '
                  %self.gitco)

        file(self.repCfgname, 'w').write(
            '[GLOBAL]\n'
            'cvsroot = %s\n'
            'gitroot = %s/\n'
            '[git/module1]\n'
            'cvspath = module1\n'
            'cvs.b1 = b1\n'
            'cvs.b2 = b2\n'
            'merge.cvs-b1 = b1 b2\n'
            'merge.cvs-b2 = b2\n'
            'merge.b2 = master\n'
            'git.master = b2\n'
            'git.b1 = b1\n'
            'prefix.b1 = SOME FIXED STRING\n'
            '[git/module3]\n'
            'cvspath = module3\n'
            'cvs.b1 = b1\n'
            'git.master = b1\n'
            % (self.cvsroot,
               self.gitroot)
            )
        # and now the other commands
        cwd1 = os.getcwd()
        self.invoke('sync')
        cwd2 = os.getcwd()
        self.assertEqual(cwd1, cwd2)
        self.assertNoTracebackLogs()

        cwd1 = os.getcwd()
        self.invoke('export')
        cwd2 = os.getcwd()
        self.assertEqual(cwd1, cwd2)
        self.assertNoTracebackLogs()

        cwd1 = os.getcwd()
        self.invoke('merge')
        cwd2 = os.getcwd()
        self.assertEqual(cwd1, cwd2)
        self.assertNoTracebackLogs()

        cwd1 = os.getcwd()
        self.invoke('help')
        cwd2 = os.getcwd()
        self.assertEqual(cwd1, cwd2)
        self.assertNoTracebackLogs()

        os.system('%s help' % self.exe)
        self.assertNoTracebackLogs()
