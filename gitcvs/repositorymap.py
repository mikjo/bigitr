#
# Read configuration files for mapping Git repositories to CVS locations
# for synchronization, including branch mappings.  Format is ini-style:
# [Path/To/Git/repository]
# gitroot = git@host # <gitroot>:<repositoryname>
# cvsroot = @servername:/path # pserver:<username> added dynamically
# cvspath = Path/To/CVS/directory
# skeleton = /path/to/skeleton
# branchfrom = <gitspec> # branch/tag/ref to branch from for new branch imports
# cvs.<branch> = <gitbranch> # CVS <branch> imports to "cvs-<gitbranch>" in Git
# git.<branch> = <cvsbranch> # Git <branch> exports to "<cvsbranch>" in CVS
# prefix.<branch> = <message> # prefix for CVS commit messages on <branch>
# email = <address> <address> # errors/warnings emailed to these addresses
#
# gitroot, cvsroot, email, and skeleton may be in a GLOBAL section, which
# will be overridden by any specific per-repository values.
#
# skeleton files are used only when creating a new cvs-* import branch.
# Note that changing the skeleton between creating cvs-* import branches
# will introduce merge conflicts when you merge cvs-* branches into
# Git development branches.  Any skeleton files other than .gitignore
# will be included in the files exported from Git branches to CVS branches.
#
# For each git.<branch>, "export-<branch>" in Git is used to track what
# on <branch> has been exported to CVS.  This branch never has anything
# committed to it.  It only gets fast-forward merges from <branch>.  It
# is used to track what is new in order to create commit messages.
#
# Can later extend if necessary to add branch-specific skeleton.branchname
# and email.branchname to override defaults.
#
# basename of git repositories must be unique

import config
import os

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
        return [(x[4:], 'cvs-' + self.get(repository, x))
                 for x in self.options(repository)
                 if x.startswith('cvs.')]

    def getExportBranchMaps(self, repository):
        return [(x[4:], self.get(repository, x), 'export-' + x[4:])
                 for x in self.options(repository)
                 if x.startswith('git.')]

    def getEmail(self, repository):
        email = self.getDefault(repository, 'email', error=False)
        if email:
            return email.split()
        return None
