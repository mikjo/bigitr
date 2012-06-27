import os
import shell

class Git(object):
    def __init__(self, ctx, repo):
        self.ctx = ctx
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

    def push(self, remote, branch):
        shell.run(self.log, 'git', 'push', remote, branch)

    def logmessages(self, since, until):
        _, messages = shell.read(self.log,
            'git', 'log', '%s..%s' %(since, until))
        return messages

    def runPreHooks(self, repository, branch):
        for hook in self.ctx.getGitPreHooks(repository, branch):
            shell.run(self.log, *hook)

    def runPostHooks(self, repository, branch):
        for hook in self.ctx.getGitPostHooks(repository, branch):
            shell.run(self.log, *hook)
