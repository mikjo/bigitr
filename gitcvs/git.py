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

import util

class Git(object):
    def __init__(self, ctx, repo):
        self.ctx = ctx
        self.repo = repo
        self.log = self.ctx.logs[repo]

    def clone(self, uri):
        return shell.run(self.log, 'git', 'clone', uri)

    def fetch(self):
        return shell.run(self.log, 'git', 'fetch', '--all')

    def reset(self):
        shell.run(self.log, 'git', 'reset', '--hard', 'HEAD')

    def clean(self):
        shell.run(self.log, 'git', 'clean', '--force', '-x', '-d')

    def pristine(self):
        if self.statusIgnored():
            self.clean()
            refs = self.refs()
            if refs:
                if 'HEAD' in (x[1] for x in refs):
                    self.reset()

    def branches(self):
        _, branches = shell.read(self.log,
            'git', 'branch', '-a')
        if branches:
            return set(x[2:].split()[0] for x in branches.split('\n') if x)
        return set()

    def branch(self):
        _, branches = shell.read(self.log,
            'git', 'branch')
        if branches:
            return [x.split()[1]
                    for x in branches.strip().split('\n')
                    if x.startswith('* ')][0]

    def refs(self):
        # no refs yet returns an error in normal operations
        rc, refs = shell.read(self.log,
            'git', 'show-ref', '--head', error=False)
        if not rc:
            return [tuple(x.split()) for x in refs.strip().split('\n')]
        return None

    def newBranch(self, branch):
        shell.run(self.log, 'git', 'branch', branch)
        shell.run(self.log, 'git', 'push', '--set-upstream', 'origin', branch)

    def trackBranch(self, branch):
        shell.run(self.log, 'git', 'branch', '--track', branch, 'origin/'+branch)
        
    def checkoutTracking(self, branch):
        shell.run(self.log,
            'git', 'checkout', '--track', 'origin/'+branch)

    def checkoutNewImportBranch(self, branch):
        shell.run(self.log, 'git', 'checkout', '--orphan', branch)
        # this command will fail for initial checkins with no files
        shell.run(self.log, 'git', 'rm', '-rf', '.', error=False)

    def checkout(self, branch):
        # line ending normalization can cause checkout to fail to
        # change branch without -f even though there are no other
        # changes in the working directory
        shell.run(self.log, 'git', 'checkout', '-f', branch)

    def listContentFiles(self):
        _, files = shell.read(self.log,
            'git', 'ls-files', '--exclude-standard', '-z')
        # --exclude-standard does not apply to .gitignore or .gitmodules
        # make sure that no .git metadata files are included in the
        # content that might be exported to CVS
        return [x for x in files.split('\0')
                if x and not os.path.basename(x).startswith('.git')]

    def status(self):
        _, output = shell.read(self.log,
            'git', 'status', '--porcelain')
        return output

    def statusIgnored(self):
        _, output = shell.read(self.log,
            'git', 'status', '--porcelain', '--ignored')
        return output

    def infoStatus(self):
        shell.run(self.log, 'git', 'status')

    def infoDiff(self, since=None, until='HEAD'):
        if since:
            shell.run(self.log, 'git', 'diff',
                      '--stat=200',
                      '--patch', '--minimal', '--irreversible-delete',
                      '%s..%s' %(since, until))
        else:
            shell.run(self.log, 'git', 'diff',
                      '--stat=200',
                      '--patch', '--minimal', '--irreversible-delete')

    def addAll(self):
        shell.run(self.log, 'git', 'add', '-A', '.')

    def mergeDefault(self, branch, message):
        return shell.run(self.log, 'git', 'merge', branch, '-m', message,
                         error=False)

    def mergeFastForward(self, branch):
        shell.run(self.log, 'git', 'merge', '--ff', '--ff-only', branch)

    def mergeIgnore(self, branch):
        shell.run(self.log, 'git', 'merge', '--strategy=ours', '--ff',
            '-m', 'branch "%s" closed' %branch, branch)

    def commit(self, message):
        shell.run(self.log, 'git', 'commit', '-m', message)

    def push(self, remote, localbranch, remotebranch):
        shell.run(self.log, 'git', 'push', remote,
            ':'.join((localbranch, remotebranch)))

    def logmessages(self, since, until):
        _, messages = shell.read(self.log,
            'git', 'log', '%s..%s' %(since, until))
        return messages

    def initializeGitRepository(self, create=True):
        gitDir = self.ctx.getGitDir()
        repoName = self.ctx.getRepositoryName(self.repo)
        repoDir = '/'.join((gitDir, repoName))
        skeleton = self.ctx.getSkeleton(self.repo)

        if not os.path.exists(repoDir):
            os.chdir(gitDir)
            self.clone(self.ctx.getGitRef(self.repo))
            os.chdir(repoDir)
            refs = self.refs()
            if not refs:
                if not create:
                    raise RuntimeError('repository %s has not been populated'
                                       %self.repo)
                # master branch needs to exist, so use skeleton or .gitignore
                if skeleton:
                    skelFiles = util.listFiles(skeleton)
                    util.copyFiles(skeleton, repoDir, skelFiles)
                else:
                    gitignore = file('/'.join((repoDir, '.gitignore')), 'w')
                    exportDir = self.ctx.getCVSExportDir(self.repo)
                    cvsignoreName = '/'.join((exportDir, '.cvsignore'))
                    if os.path.exists(cvsignoreName):
                        gitignore.write(file(cvsignoreName).read())
                    gitignore.close()
                self.addAll()
                self.commit('create new empty master branch')
                self.push('origin', 'master', 'master')

    def runImpPreHooks(self, branch):
        for hook in self.ctx.getGitImpPreHooks(self.repo, branch):
            shell.run(self.log, *hook)

    def runImpPostHooks(self, branch):
        for hook in self.ctx.getGitImpPostHooks(self.repo, branch):
            shell.run(self.log, *hook)

    def runExpPreHooks(self, branch):
        for hook in self.ctx.getGitExpPreHooks(self.repo, branch):
            shell.run(self.log, *hook)

    def runExpPostHooks(self, branch):
        for hook in self.ctx.getGitExpPostHooks(self.repo, branch):
            shell.run(self.log, *hook)
