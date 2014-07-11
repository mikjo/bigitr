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

import os
import shell
import tempfile

from bigitr import util

# One CVS checkout per branch, because CVS switches branches slowly/poorly,
# so there is one CVS object per branch, not per repository.
# No checkout directory is created for exporting

class CVSError(RuntimeError):
    pass

def setCVSROOT(fn):
    def wrapper(self, *args, **kwargs):
        self.setEnvironment()
        fn(self, *args, **kwargs)
    return wrapper

def inCVSPATH(fn):
    def wrapper(self, *args, **kwargs):
        oldDir = os.getcwd()
        os.chdir(self.path)
        try:
            fn(self, *args, **kwargs)
        except Exception as e:
            try:
                # Failed CVS operations may leave checkout in inconsistent state.
                # Remove the checkout to prevent trouble next time around
                util.removeRecursive(self.path)
            finally:
                raise CVSError(e)
        finally:
            os.chdir(oldDir)
    return wrapper

def inCVSDIR(fn):
    def wrapper(self, *args, **kwargs):
        oldDir = os.getcwd()
        os.chdir(os.path.dirname(self.path))
        try:
            fn(self, *args, **kwargs)
        finally:
            os.chdir(oldDir)
    return wrapper

class CVS(object):
    SYMBOLIC_BRANCH_MAP = {
        '@{trunk}': None,
        }

    def __init__(self, ctx, repo, branch):
        self.ctx = ctx
        self.repo = repo
        self.location = self.ctx.getCVSPath(repo)
        self.path = ctx.getCVSBranchCheckoutDir(repo, branch)
        self.pathbase = os.path.basename(self.path)
        self.branch = branch
        self.mapped_branch = self.SYMBOLIC_BRANCH_MAP.get(branch, branch)
        self.log = self.ctx.logs[repo]
        self.root = ctx.getCVSRoot(repo)

    def setEnvironment(self):
        os.environ['CVSROOT'] = self.root

    def listContentFiles(self):
        allfiles = []
        dirlen = len(self.path) + 1
        for root, dirs, files in os.walk(self.path):
            if 'CVS' in dirs:
                dirs.remove('CVS') 
            allfiles.extend(['/'.join((root, x))[dirlen:] for x in files])
        return allfiles

    @setCVSROOT
    def export(self, targetDir):
        cmd = ['cvs', 'export', '-kk', '-d', targetDir]
        if self.mapped_branch is not None:
            cmd.extend(('-r', self.branch))
        else:
            cmd.extend(('-D', 'now'))
        cmd.append(self.location)
        shell.run(self.log, *cmd)

    @setCVSROOT
    @inCVSDIR
    def checkout(self):
        cmd = ['cvs', 'checkout', '-kk', '-d', self.pathbase]
        if self.mapped_branch is not None:
            cmd.extend(('-r', self.branch))
        cmd.append(self.location)
        shell.run(self.log, *cmd)

    @inCVSPATH
    def infoDiff(self):
        # cvs diff uses non-zero return codes for success
        shell.run(self.log, 'cvs', 'diff', error=False)

    @inCVSPATH
    def update(self):
        shell.run(self.log, 'cvs', 'update', '-kk', '-d')

    @inCVSPATH
    def deleteFiles(self, fileNames):
        if fileNames:
            for fileName in fileNames:
                os.remove(fileName)
            shell.run(self.log, 'cvs', 'remove', *fileNames)

    def copyFiles(self, sourceDir, fileNames):
        'call addFiles for any files being added rather than updated'
        util.copyFiles(sourceDir, self.path, fileNames)

    @inCVSPATH
    def addDirectories(self, dirNames):
        for dirName in dirNames:
            parent = os.path.dirname(dirName)
            if parent and parent != '/' and not os.path.exists(parent + '/CVS'):
                self.addDirectories((parent,))
            if not os.path.exists(dirName + '/CVS'):
                shell.run(self.log, 'cvs', 'add', dirName)

    @inCVSPATH
    def addFiles(self, fileNames):
        if fileNames:
            shell.run(self.log, 'cvs', 'add', '-kk', *fileNames)

    @inCVSPATH
    def commit(self, message):
        fd, name = tempfile.mkstemp('.bigitr')
        os.write(fd, message)
        # flat list: ['-s', 'A=a', '-s', 'B=b']
        cvsvars = sum([['-s', x]
                       for x in self.ctx.getCVSVariables(self.repo)], [])
        if self.mapped_branch is not None:
            commitargs = ['commit', '-r', self.branch, '-R', '-F', name]
        else:
            commitargs = ['commit', '-R', '-F', name]
        try:
            shell.run(self.log, 'cvs', *(cvsvars + commitargs))
        finally:
            os.remove(name)
            os.close(fd)

    @inCVSPATH
    def runPreHooks(self):
        for hook in self.ctx.getCVSPreHooks(self.repo, self.branch):
            shell.run(self.log, *hook)

    @inCVSPATH
    def runPostHooks(self):
        for hook in self.ctx.getCVSPostHooks(self.repo, self.branch):
            shell.run(self.log, *hook)
