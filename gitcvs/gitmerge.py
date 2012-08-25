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

from gitcvs import errhandler
from gitcvs import util

class Merger(object):
    def __init__(self, ctx):
        self.ctx = ctx
        self.err = errhandler.Errors(ctx)

    def mergeBranches(self, repository, Git, requestedBranch=None):
        onerror = self.ctx.getImportError()
        try:
            for gitbranch in self.ctx.getMergeBranchMaps(repository).keys():
                if requestedBranch is None or gitbranch == requestedBranch:
                    self.mergeBranch(repository, Git, gitbranch)
        except Exception as e:
            self.err(repository, onerror)

    @util.saveDir
    def mergeBranch(self, repository, Git, gitbranch):
        Git.initializeGitRepository(create=False)
        self.mergeFrom(repository, Git, gitbranch)

    def mergeFrom(self, repository, Git, gitbranch):
        success = True
        # try to merge downstream branches even if there was nothing to
        # commit, because a merge conflict might have been resolved
        if not self.merge(repository, Git, gitbranch):
            success = False

        # Status can report clean with .gitignored files existing
        # Remove any .gitignored files added by the "cvs export"
        Git.pristine()

        if not success:
            raise RuntimeError('merge failed for branch %s: see %s' %(
                gitbranch, Git.log.thiserr))

    def merge(self, repository, Git, gitbranch):
        success = True

        Git.pristine()
        for target in self.ctx.getMergeBranchMaps(repository
                ).get(gitbranch, set()):
            Git.checkout(target)
            Git.mergeFastForward('origin/' + target)
            mergeMsg = "Automated merge '%s' into '%s'" %(gitbranch, target)
            rc = Git.mergeDefault(gitbranch, mergeMsg)
            if rc != 0:
                Git.log.mailLastOutput(mergeMsg)
                success = False
            else:
                Git.push('origin', target, target)
                Git.runImpPostHooks(target)
                rc = self.merge(repository, Git, target)
                if not rc:
                    success = False

        return success
