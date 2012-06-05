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
    def trackBranch(Git, branch, branches, repository, createBranch=False):
        if branch not in branches:
            if 'remotes/origin/' + branch in branches:
                Git.trackBranch(branch)
            else:
                if not createBranch:
                    raise KeyError('branch %s not found for repository %s'
                                   %(branch, repository))
                Git.newBranch(branch)


    def exportAll(self):
        for repository in self.ctx.getRepositories():
            Git = git.Git(self.ctx, repository)
            self.exportBranches(repository, Git)

    def exportBranches(self, repository, Git):
        for gitbranch, cvsbranch, exportbranch in self.ctx.getExportBranchMaps(repository):
            CVS = cvs.CVS(self.ctx, repository, cvsbranch, self.username)
            self.exportgit(repository, Git, CVS, gitbranch, exportbranch)

    def exportgit(self, repository, Git, CVS, gitbranch, exportbranch):
        gitDir = self.ctx.getGitDir()
        cvsDir = os.path.dirname(CVS.path)
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
        Git.fetch()
        # clean up after any garbage left over from previous runs so
        # that we can change branches
        Git.pristine()
        branches = Git.branches()
        self.trackBranch(Git, gitbranch, branches, repository, createBranch=False)
        Git.checkout(gitbranch)
        Git.mergeFastForward('origin/' + gitbranch)
        self.trackBranch(Git, exportbranch, branches, repository, createBranch=True)

        GitList = Git.listContentFiles()
        GitFileSet = set(GitList)
        DeletedFiles = CVSFileSet - GitFileSet
        # even if .cvsignore files are deleted in git, do not remove them in CVS
        DeletedFiles -= set(x for x in DeletedFiles
                            if x.split('/')[-1] == '.cvsignore')
        AddedFiles = GitFileSet - CVSFileSet
        CommonFiles = GitFileSet.intersection(CVSFileSet)
        GitDirs = set(os.path.dirname(x) for x in GitFileSet)
        CVSDirs = set(os.path.dirname(x) for x in CVSFileSet)
        AddedDirs = GitDirs - CVSDirs

        if not GitFileSet - set(('.gitignore',)):
            # do not push an empty branch in order to avoid deleting a
            # whole CVS branch due to configuration failure
            raise RuntimeError("Not committing empty branch '%s'"
                               " from git branch '%s'" %(CVS.branch, gitbranch))

        GitMessages = Git.logmessages(exportbranch, gitbranch)
        if GitMessages == '':
            # if there are any differences this is the first export
            GitMessages = 'Initial export to CVS from git branch %s' %gitbranch
        prefix = self.ctx.getBranchPrefix(repository, CVS.branch)
        if prefix:
            GitMessages = '\n\n'.join((prefix, GitMessages))

        Git.infoDiff(exportbranch, gitbranch)

        CVS.deleteFiles(sorted(list(DeletedFiles)))
        CVS.copyFiles(repoDir, sorted(list(CommonFiles.union(AddedFiles))))
        # directories need to be added first, and here sorted order
        # causes directories to be specified in top-down order
        CVS.addFiles(sorted(list(AddedDirs)))
        CVS.addFiles(sorted(list(AddedFiles)))

        CVS.commit(GitMessages)
        Git.checkout(exportbranch)
        Git.mergeFastForward(gitbranch)
        Git.push('origin', exportbranch)
