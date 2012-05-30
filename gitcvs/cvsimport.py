import os
import shell
import time

import git
import cvs

class Importer(object):
    def __init__(self, ctx, username):
        self.ctx = ctx
        self.username = username

    def importAll(self):
        for repository in self.ctx.getRepositories():
            Git = git.Git(self.ctx, repository)
            self.importBranches(repository, Git)

    def importBranches(self, repository, Git):
        for cvsbranch, gitbranch in self.ctx.getImportBranchMaps(repository):
            CVS = cvs.CVS(self.ctx, repository, cvsbranch, self.username)
            self.importcvs(repository, Git, CVS, cvsbranch, gitbranch)

    def importcvs(self, repository, Git, CVS, cvsbranch, gitbranch):
        gitDir = self.ctx.getGitDir()
        repoName = self.ctx.getRepositoryName(repository)
        repoDir = '/'.join((gitDir, repoName))
        if not os.path.exists(repoDir):
            os.chdir(gitDir)
            Git.clone(self.ctx.getGitRef(repository))
            os.chdir(repoDir)
            refs = Git.refs()
            if not refs:
                # master branch needs to exist
                # FIXME: if skeleton, add skeleton; else empty .gitignore
                file('/'.join((repoDir, '.gitignore')), 'w')
                Git.addAll()
                Git.commit('create new empty master branch')
                Git.push('origin', 'master')

        os.chdir(repoDir)
        # clean up after any garbage left over from previous runs so
        # that we can change branches
        Git.pristine()
        addSkeleton = False
        branches = Git.branches()
        if gitbranch not in branches:
            if 'remotes/origin/' + gitbranch in branches:
                # check out existing remote branch
                Git.checkoutTracking(gitbranch)
            else:
                # check out a new "orphan" branch
                Git.checkoutNewImportBranch(gitbranch)
                addSkeleton = True
        else:
            if Git.branch() != gitbranch:
                Git.checkout(gitbranch)

        for filename in Git.listContentFiles():
            os.remove(filename)

        os.chdir(gitDir)
        ignoreFiles = set(CVS.listFiles(repoName))
        CVS.export(repoName)
        exportedFiles = set('/'.join((repoName, x))
                            for x in set(CVS.listFiles(repoName)) - ignoreFiles)
        CVS.cleanKeywords(sorted(list(exportedFiles)))
        if addSkeleton:
            pass
            #FIXME
        os.chdir(repoDir)
        if Git.status():
            # there is some change to commit
            Git.infoStatus()
            Git.infoDiff()
            Git.addAll()
            # FIXME: try to create a commit message that includes all
            # the CVS commit messages since the previous commit, de-duplicated
            Git.commit('import from CVS as of %s' %time.asctime())
            Git.push('origin', gitbranch)
