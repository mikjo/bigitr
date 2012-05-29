#
# Read configuration files for cvs/git synchronization
# [global]
# gitdir = /path/to/directory/holding/git/repositories
# logdir = /path/to/log/directory
# mailfrom = sendinguser@host
# smarthost = smtp.smarthost.name
# [import]
# onerror = abort # abort|warn|continue
# resetids = true # false to leave $cvsid:...$ alone
# [export]
# preimport = true # false to overwrite whatever is in CVS
# onerror = abort # abort|warn|continue
# cvsdir = /path/to/directory/for/cvs/checkouts/for/branch/imports
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
            'onerror': 'abort',
            'resetids': 'true'})

    def getGitDir(self):
        return self.get('global', 'gitdir')

    def getLogDir(self):
        return self.get('global', 'logdir')

    def getMailFrom(self):
        return self.get('global', 'mailfrom')

    def getSmartHost(self):
        return self.get('global', 'smarthost')

    def getImportError(self):
        return onerror[self.get('import', 'onerror')]
    
    def getResetIds(self):
        return self.getboolean('import', 'resetids')

    def getExportPreImport(self):
        return self.getboolean('export', 'preimport')

    def getExportError(self):
        return onerror[self.get('export', 'onerror')]

    def getExportCVSDir(self):
        return self.get('export', 'cvsdir')

