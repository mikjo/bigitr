# One application context for different content

import os

import appconfig
import repositorymap
import log

class Context(object):
    def __init__(self, appConfig, repoConfig):
        # cannot be a mixin because shared base class collides
        self._ac = appconfig.AppConfig(appConfig)
        self._rm = repositorymap.RepositoryConfig(repoConfig)
        self.logs = log.LogCache(self)
    
    def __getattr__(self, attr):
        # fallback: multiplex rather than mixin
        if attr in dir(self._ac):
            return getattr(self._ac, attr)
        if attr in dir(self._rm):
            return getattr(self._rm, attr)
        # this will raise AttributeError with an appropriate message
        return self.__getattribute__(attr)

    def getCVSBranchCheckoutDir(self, repository, cvsbranch):
        base = self.getExportCVSDir()
        repo = self.getRepositoryName(repository)
        checkout = os.path.basename(self.getCVSPath(repository))
        return '/'.join((base, repo, cvsbranch, checkout))
