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
#
# high-level driver for synchronization process

import os

from bigitr import cvsimport
from bigitr import errhandler
from bigitr import gitexport
from bigitr import git
from bigitr import shell

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
            except shell.ErrorExitCode, e:
                # report errors from commands that fail
                Git.log.mailLastOutput(str(e))
                self.err.report(repository)
            except:
                # report and keep going; no reason for one
                # repository to keep other repositories from synchronizing
                self.err.report(repository)

    def synchronize(self, repository, Git):
        if self.ctx.getExportPreImport():
            self.imp.importBranches(repository, Git)
        self.exp.exportBranches(repository, Git)
        self.imp.importBranches(repository, Git)
