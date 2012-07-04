#
# Read configuration files for mapping Git repositories to CVS locations
# for synchronization, including branch mappings.  Format is ini-style:
# basename of git repositories must be unique

import config
import os
import shlex

class RepositoryConfig(config.Config):
    def __init__(self, configFileName):
        config.Config.__init__(self, configFileName)
        # enforce uniqueness
        repos = {}
        for r in self.getRepositories():
            name = self.getRepositoryName(r)
            if name in repos:
                raise KeyError('Duplicate repository name %s: %s and %s'
                               %(name, repos[name], r))
            repos[name] = r
        self.requireAbsolutePaths('skeleton')

    def getDefault(self, section, key, error=True):
        if self.has_option(section, key):
            return self.get(section, key)
        if self.has_option('GLOBAL', key):
            return self.get('GLOBAL', key)
        if not error:
            return None
        # raise contextually meaningful NoOptionError using self.get
        self.get(section, key)

    def getOptional(self, section, key):
        if self.has_option(section, key):
            return self.get(section, key)
        return None

    def getRepositories(self):
        return set(self.sections()) - set(('GLOBAL',))

    @staticmethod
    def getRepositoryName(repository):
        return os.path.basename(repository)

    def getCVSRoot(self, repository, username):
        return ':pserver:%s%s' %(username, self.getDefault(repository, 'cvsroot'))

    def getGitRef(self, repository):
        return ':'.join((self.getDefault(repository, 'gitroot'), repository))

    def getCVSPath(self, repository):
        return self.get(repository, 'cvspath')

    def getSkeleton(self, repository):
        return self.getDefault(repository, 'skeleton', error=False)

    def getBranchFrom(self, repository):
        return self.getOptional(repository, 'branchfrom')

    def getBranchPrefix(self, repository, branch):
        optname = 'prefix.'+branch
        return self.getOptional(repository, optname)

    def getImportBranchMaps(self, repository):
        'return: [(cvsbranch, gitbranch), ...]'
        return [(x[4:], 'cvs-' + self.get(repository, x))
                 for x in sorted(self.options(repository))
                 if x.startswith('cvs.')]

    def getExportBranchMaps(self, repository):
        'return: [(gitbranch, cvsbranch, exportbranch), ...]'
        return [(x[4:], self.get(repository, x), 'export-' + x[4:])
                 for x in sorted(self.options(repository))
                 if x.startswith('git.')]

    def getMergeBranchMaps(self, repository):
        'return: {sourcebranch, set(targetbranch, targetbranch, ...), ...}'
        return dict((x[6:], set(self.get(repository, x).strip().split()))
                    for x in sorted(self.options(repository))
                    if x.startswith('merge.'))

    def getHook(self, type, when, repository):
        return self.getDefault(repository, when+'hook.'+type, error=False)

    def getHookDir(self, direction, type, when, repository):
        if direction:
            return self.getDefault(repository, when+'hook.'+direction+'.'+type,
                                   error=False)
        return None

    def getHookBranch(self, type, when, repository, branch):
        return self.getDefault(repository, when+'hook.'+type+'.'+branch,
                               error=False)

    def getHookDirBranch(self, direction, type, when, repository, branch):
        if direction:
            return self.getDefault(repository, when+'hook.'+direction+'.'+type+'.'+branch,
                                   error=False)
        return None

    def getHooksBranch(self, type, direction, when, repository, branch):
        return [shlex.split(x) for x in
                (self.getHook(type, when, repository),
                 self.getHookDir(direction, type, when, repository),
                 self.getHookBranch(type, when, repository, branch),
                 self.getHookDirBranch(direction, type, when, repository, branch))
                if x]

    def getGitImpPreHooks(self, repository, branch):
        return self.getHooksBranch('git', 'imp', 'pre', repository, branch)

    def getGitImpPostHooks(self, repository, branch):
        return self.getHooksBranch('git', 'imp', 'post', repository, branch)

    def getGitExpPreHooks(self, repository, branch):
        return self.getHooksBranch('git', 'exp', 'pre', repository, branch)

    def getGitExpPostHooks(self, repository, branch):
        return self.getHooksBranch('git', 'exp', 'post', repository, branch)

    def getCVSPreHooks(self, repository, branch):
        return self.getHooksBranch('cvs', None, 'pre', repository, branch)

    def getCVSPostHooks(self, repository, branch):
        return self.getHooksBranch('cvs', None, 'post', repository, branch)

    def getEmail(self, repository):
        email = self.getDefault(repository, 'email', error=False)
        if email:
            return email.split()
        return None
