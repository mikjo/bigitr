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
# Read configuration file for Git / CVS synchronization daemon

import glob
import re

from bigitr import config

class DaemonConfig(config.Config):
    def __init__(self, configFileName):
        config.Config.__init__(self, configFileName, {
            'mailall': 'false',
            'smarthost': 'localhost'})
        self.requireAbsolutePaths('repoconfig', 'appconfig')
        self.timeRE = re.compile(
            r'\s*((?P<d>\d+)d\s*)?'
            r'((?P<h>\d+)h\s*)?'
            r'((?P<m>\d+)m\s*)?'
            r'((?P<s>\d+)s?)?', re.I)

    def parallelConversions(self):
        'number of repositories to process in parallel'
        return int(self.getDefault('GLOBAL', 'parallel', 1))

    def getPollFrequency(self):
        '[%dd][%dh][%dm][%d[s]] minimum frequency for polling full sync'
        # minimum time to wait since last poll started, per repository
        timespec = self.getGlobalDefault('GLOBAL', 'pollfrequency', '5m')
        return self._parseTimeSpec(timespec)

    def getFullSyncFrequency(self):
        '[%dd][%dh][%dm][%d[s]] minimum frequency for unconditional full sync'
        # minimum time to wait to start a full sync, per repository
        timespec = self.getGlobalDefault('GLOBAL', 'syncfrequency', '1d')
        return self._parseTimeSpec(timespec)

    def getEmail(self):
        'email for daemon tracebacks'
        email = self.getDefault('GLOBAL', 'email', None)
        if email:
            return email.split()
        return None

    def getMailFrom(self):
        return self.getDefault('GLOBAL', 'mailfrom', None)

    def getMailAll(self):
        'add administrator to all emails in lieu of seeing console output'
        return self.getboolean('GLOBAL', 'mailall')

    def getSmartHost(self):
        return self.get('GLOBAL', 'smarthost')

    def getApplicationContexts(self):
        return set(self.sections()) - set(('GLOBAL',))

    def getAppConfig(self, section):
        return self.getGlobalFallback(section, 'appconfig')

    def getRepoConfigs(self, section):
        'space-separated globs of paths to repository config files'
        repoConfig = []
        for repoGlob in self.getGlobalFallback(section, 'repoconfig').split():
            repoConfig.extend(glob.glob(repoGlob))
        return repoConfig

    def _parseTimeSpec(self, timespec):
        times = self.timeRE.search(timespec).groupdict()
        # convert None to 0, strings to integers
        times = dict((x, int(y) if y else 0) for x, y in times.items())
        return times['d'] * 86000 + times['h'] * 3600 + times['m'] * 60 + times['s']
