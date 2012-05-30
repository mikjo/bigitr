import os
import shell
import time

import git
import cvs

class Exporter(object):
    def __init__(self, ctx, username):
        self.ctx = ctx
        self.username = username

    @staticmethod
    def trackBranch(Git, branch, branches, createBranch=False):
        if branch not in branches:
            if 'remotes/origin/' + branch in branches:
                Git.trackBranch(branch)
            else:
                if not createBranch:
                    raise KeyError('branch %s not found for repository %s'
                                   %(gitbranch, repository))
                Git.newBranch(exportbranch)


    def exportAll(self):
        for repository in self.ctx.getRepositories():
            Git = git.Git(self.ctx, repository)
            self.exportBranches(repository, Git)

    def exportBranches(self, repository, Git):
        for cvsbranch, gitbranch, exportbranch in self.ctx.getExportBranchMaps(repository):
            CVS = cvs.CVS(self.ctx, repository, cvsbranch, self.username)
            self.exportgit(repository, Git, CVS, gitbranch, exportbranch)

    def exportgit(self, repository, Git, CVS, gitbranch, exportbranch):
        gitDir = self.ctx.getGitDir()
        cvsDir = os.path.dirname(cvs.path)
        repoName = self.ctx.getRepositoryName(repository)
        repoDir = '/'.join((gitDir, repoName))

        if not os.path.exists(repoDir):
            os.chdir(gitDir)
            Git.clone(self.ctx.getGitRef(repository))
        if not os.path.exists(cvsDir):
            os.makedirs(cvsDir)
        if os.path.exists(CVS.path):
            CVS.update()
        else:
            CVS.checkout()
        CVSList = CVS.listContentFiles()
        CVSFileSet = set(CVSList)

        os.chdir(repoDir)
        # clean up after any garbage left over from previous runs so
        # that we can change branches
        Git.reset()
        branches = Git.branches()
        self.trackBranch(Git, gitbranch, branches, createBranch=False)
        Git.checkout(gitbranch)
        self.trackBranch(Git, exportbranch, branches, createBranch=True)

        GitList = Git.listContentFiles()
        GitFileSet = set(GitList)
        DeletedFiles = CVSFileSet - GitFileSet
        AddedFiles = GitFileSet - CVSFileSet
        CommonFiles = GitFileSet.intersection(CVSFileSet)
        GitDirs = set(os.path.dirname(x) for x in GitFileSet)
        CVSDirs = set(os.path.dirname(x) for x in CVSFileSet)
        AddedDirs = GitDirs = CVSDirs

        GitMessages = Git.logmessages(exportbranch, gitbranch)
        prefix = self.ctx.getBranchPrefix(repository, CVS.branch)
        if prefix:
            GitMessages = '\n\n'.join((prefix, GitMessages))

        git.infoDiff(exportbranch, gitbranch)

        CVS.deleteFiles(sorted(list(DeletedFiles)))
        CVS.copyFiles(repoDir, sorted(list(CommonFiles+AddedFiles)))
        # directories need to be added first, and here sorted order
        # causes directories to be specified in top-down order
        CVS.addFiles(repoDir, sorted(list(AddedDirs)))
        CVS.addFiles(repoDir, sorted(list(AddedFiles)))

        CVS.commit(GitMessages)
        # FIXME: test that a failed commit (from a competing commit)
        # raises an error and thus causes exportbranch to be left alone
        # so that this can be retried
        Git.mergeIgnore(exportbranch)
        Git.push(exportbranch)
