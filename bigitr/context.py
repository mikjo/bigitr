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

# One application context for different content

import os

from bigitr import appconfig
from bigitr import repositorymap
from bigitr import log
from bigitr import mail

class Context(object):
    def __init__(self, appConfig, repoConfig):
        # cannot be a mixin because shared base class collides
        if isinstance(appConfig, appconfig.AppConfig):
            self._ac = appConfig
        else:
            self._ac = appconfig.AppConfig(appConfig)
        if isinstance(repoConfig, repositorymap.RepositoryConfig):
            self._rm = repoConfig
        else:
            self._rm = repositorymap.RepositoryConfig(repoConfig)
        self.logs = log.LogCache(self)
        self.mails = mail.MailCache(self)
    
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

    def getCVSExportDir(self, repository):
        base = self.getImportCVSDir()
        repo = self.getRepositoryName(repository)
        checkout = os.path.basename(self.getCVSPath(repository))
        return '/'.join((base, repo, checkout))
