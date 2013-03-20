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
import time

from bigitr import errhandler
from bigitr import cvs
from bigitr import git
from bigitr import util

class Exporter(object):
    def __init__(self, ctx):
        self.ctx = ctx
        self.err = errhandler.Errors(ctx)

    def exportAll(self):
        for repository in self.ctx.getRepositories():
            Git = git.Git(self.ctx, repository)
            self.exportBranches(repository, Git)

    def exportBranches(self, repository, Git, requestedBranch=None):
        onerror = self.ctx.getExportError()
        for gitbranch, cvsbranch, exportbranch in self.ctx.getExportBranchMaps(
                repository):
            if requestedBranch is None or gitbranch == requestedBranch:
                CVS = cvs.CVS(self.ctx, repository, cvsbranch)
                try:
                    self.exportgit(repository, Git, CVS, gitbranch, exportbranch)
                except Exception as e:
                    self.err(repository, onerror)

    @util.saveDir
    def exportgit(self, repository, Git, CVS, gitbranch, exportbranch):
        gitDir = self.ctx.getGitDir()
        repoName = self.ctx.getRepositoryName(repository)
        repoDir = '/'.join((gitDir, repoName))
        originExportBranch = 'remotes/origin/'+exportbranch
        exportbranches = set((exportbranch, originExportBranch))

        self.cloneGit(repository, Git, repoDir)

        branches = self.prepareGitClone(repository, Git, gitbranch)
        if (branches - exportbranches) == branches:
            GitMessages = 'Initial export to CVS from git branch %s' %gitbranch
        else:
            GitMessages = Git.logmessages(originExportBranch, gitbranch)
            if GitMessages == '':
                # There have been no changes in Git since the last export,
                # so there is nothing to export. (If CVS shows changes,
                # the changes should be due to normalization such as
                # populated CVS keywords checked into Git.)
                return

        # it is not recommended that hooks commit, but if they do, they will
        # have commit messages that are automated and should not show up in
        # CVS commits. Therefore, run the hooks after getting the Git commit
        # messages. However, by the same token, they must be run before
        # calculating fileSets.

        Git.runExpPreHooks(gitbranch)

        # wait until we think there are changes to export before checking
        # out from CVS, since this checkout/update can be slow
        self.checkoutCVS(CVS)

        GitFileSet, DeletedFiles, AddedFiles, CommonFiles, AddedDirs = self.calculateFileSets(CVS, Git)

        if not GitFileSet:
            # do not push an empty branch in order to avoid deleting a
            # whole CVS branch due to configuration failure
            raise RuntimeError("Not committing empty branch '%s'"
                               " from git branch '%s'" %(CVS.branch, gitbranch))

        CVSMetaData = [x for x in AddedDirs if x == 'CVS' or x.endswith('/CVS')]
        if CVSMetaData:
            raise RuntimeError("Not exporting with CVS metadata included"
                               " in Git repository: '%s'" %
                               ' '.join(CVSMetaData))

        prefix = self.ctx.getBranchPrefix(repository, CVS.branch)
        if prefix:
            GitMessages = '\n\n'.join((prefix, GitMessages))

        if originExportBranch in branches:
            Git.infoDiff(originExportBranch, gitbranch)

        CVS.deleteFiles(sorted(list(DeletedFiles)))
        CVS.copyFiles(repoDir, sorted(list(CommonFiles.union(AddedFiles))))
        # directories need to be added first, and here sorted order
        # causes directories to be specified in top-down order
        CVS.addDirectories(sorted(list(AddedDirs)))
        CVS.addFiles(sorted(list(AddedFiles)))

        # before infoDiff so that changes are represented in the infoDiff
        CVS.runPreHooks()

        CVS.infoDiff()
        # email with CVS.log.lastOutput() and GitMessages
        CVS.commit(GitMessages)
        Git.push('origin', gitbranch, exportbranch)

        # posthooks only after successfully pushing export- merge to origin
        CVS.runPostHooks()
        Git.runExpPostHooks(gitbranch)

    def cloneGit(self, repository, Git, repoDir):
        if not os.path.exists(repoDir):
            os.chdir(self.ctx.getGitDir())
            Git.clone(self.ctx.getGitRef(repository))
        os.chdir(repoDir)

    def checkoutCVS(self, CVS):
        cvsDir = os.path.dirname(CVS.path)
        if not os.path.exists(cvsDir):
            os.makedirs(cvsDir)
        if os.path.exists(CVS.path):
            CVS.update()
        else:
            CVS.checkout()
            if not os.path.exists(CVS.path):
                raise RuntimeError("CVS branch '%s' for location '%s' does not exist"
                                   %(CVS.branch, CVS.location))


    def prepareGitClone(self, repository, Git, gitbranch):
        Git.fetch()
        # clean up after any garbage left over from previous runs so
        # that we do not copy files not managed, at least on this branch,
        # into CVS
        Git.pristine()
        branches = Git.branches()
        self.trackBranch(repository, Git, gitbranch, branches)
        Git.checkout(gitbranch)
        try:
            Git.mergeFastForward('origin/' + gitbranch)
        except:
            # if the fast forward failed after reset --hard HEAD, then the
            # repository is in an indeterminate state, so remove it; it will
            # be recreated on the next operation
            os.chdir(self.ctx.getGitDir())
            util.removeRecursive(self.ctx.getRepositoryName(repository))
            raise
        return branches

    def calculateFileSets(self, CVS, Git):
        CVSList = CVS.listContentFiles()
        CVSFileSet = set(CVSList)
        GitList = Git.listContentFiles()
        GitFileSet = set(GitList)
        DeletedFiles = CVSFileSet - GitFileSet
        # even if .cvsignore files are deleted in git, do not remove them in CVS
        DeletedFiles -= set(x for x in DeletedFiles
                            if x.split('/')[-1] == '.cvsignore')
        AddedFiles = GitFileSet - CVSFileSet
        CommonFiles = GitFileSet.intersection(CVSFileSet)
        GitDirs = set(os.path.dirname(x) for x in GitFileSet)
        GitDirs = set(x for x in GitDirs if x)
        CVSDirs = set(os.path.dirname(x) for x in CVSFileSet)
        CVSDirs = set(x for x in CVSDirs if x)
        AddedDirs = GitDirs - CVSDirs
        return GitFileSet, DeletedFiles, AddedFiles, CommonFiles, AddedDirs

    @staticmethod
    def trackBranch(repository, Git, branch, branches):
        if branch not in branches:
            if 'remotes/origin/' + branch in branches:
                Git.trackBranch(branch)
            else:
                raise KeyError('branch %s not found for repository %s'
                               %(branch, repository))
