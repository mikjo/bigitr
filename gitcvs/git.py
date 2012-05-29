import os
import shell

class Git(object):
    def __init__(self, ctx, repo):
        self.ctx = ctx
        self.log = self.ctx.logs[repo]

    def clone(self, uri):
        return shell.run(self.log,
            'git', 'clone', uri)

    def reset(self):
        shell.run(self.log, 'git', 'reset', '--hard', 'HEAD')

    def branches(self):
        _, branches = shell.read(self.log,
            'git', 'branch', '-a')
        return set(x[2:].split()[0] for x in branches.strip().split('\n'))

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
        shell.run(self.log, 'git', 'rm', '-rf', '.')

    def checkout(self, branch):
        shell.run(self.log, 'git', 'checkout', branch)

    def listContentFiles(self):
        _, files = shell.read(self.log,
            'git', 'ls-files', '--exclude-standard', '-z')
        # --exclude-standard does not apply to .gitignore or .gitmodules
        return [x for x in files.split('\0') if x and not '.git' in x]

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
        shell.run(self.log, 'git', 'add', '.')

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
