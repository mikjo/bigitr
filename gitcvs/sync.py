# high-level driver for synchronization process

import os

import cvsimport
import errhandler
import gitexport
import git

class Synchronizer(object):
    def __init__(self, ctx):
        self.ctx = ctx
        self.imp = cvsimport.Importer(ctx)
        self.exp = gitexport.Exporter(ctx)
        self.err = errhandler.Errors(ctx)

    def synchronizeAll(self):
        for repository in self.ctx.getRepositories():
            Git = git.Git(self.ctx, repository)
            try:
                self.synchronize(repository, Git)
            except:
                # report and keep going; no reason for one
                # repository to keep other repositories from synchronizing
                self.err.report(repository)

    def synchronize(self, repository, Git):
        if self.ctx.getExportPreImport():
            self.imp.importBranches(repository, Git)
        self.exp.exportBranches(repository, Git)
        self.imp.importBranches(repository, Git)
