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
# Read configuration files for cvs/git synchronization
#

import config

ABORT = 0
WARN = 1
CONTINUE = 2
onerror = {
    'abort': ABORT,
    'warn': WARN,
    'continue': CONTINUE,
}


class AppConfig(config.Config):
    def __init__(self, configFileName):
        config.Config.__init__(self, configFileName, {
            'compresslogs': 'true',
            'onerror': 'abort',
            'preimport': 'true',
            'smarthost': 'localhost'})

    def getCompressLogs(self):
        return self.getboolean('global', 'compresslogs')

    def getGitDir(self):
        return self.get('global', 'gitdir')

    def getLogDir(self):
        return self.get('global', 'logdir')

    def getMailFrom(self):
        if self.has_option('global', 'mailfrom'):
            return self.get('global', 'mailfrom')
        return None

    def getSmartHost(self):
        return self.get('global', 'smarthost')

    def getImportError(self):
        return onerror[self.get('import', 'onerror')]

    def getImportCVSDir(self):
        return self.get('import', 'cvsdir')
    
    def getExportPreImport(self):
        return self.getboolean('export', 'preimport')

    def getExportError(self):
        return onerror[self.get('export', 'onerror')]

    def getExportCVSDir(self):
        return self.get('export', 'cvsdir')
