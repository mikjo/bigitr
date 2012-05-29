import gzip
import os
import stat
import time
import weakref

class Log(object):
    def __init__(self, ctx, repo, cache):
        self.ctx = ctx
        self.cache = None
        if cache is not None:
            self.cache = weakref.ref(cache)
        self.repo = repo
        logDir = ctx.getLogDir()
        repoLogDir = '/'.join((logDir, ctx.getRepositoryName(repo)))
        basename = time.strftime('%Y%m%d-%H:%M:%S')
        if not os.path.exists(repoLogDir):
            os.makedirs(repoLogDir)
        self.thislog = '%s/%s.log' %(repoLogDir, basename)
        self.thiserr = '%s/%s.err' %(repoLogDir, basename)
        self.stdout = os.open(self.thislog, os.O_CREAT|os.O_RDWR, 0700)
        self.stderr = os.open(self.thiserr, os.O_CREAT|os.O_RDWR, 0700)

    @staticmethod
    def compress(filename):
        gzo = gzip.GzipFile(filename + '.gz', 'w', 9)
        gzo.writelines(open(filename))
        gzo.close()

    def close(self):
        outstat = os.fstat(self.stdout)
        errstat = os.fstat(self.stderr)
        os.close(self.stdout)
        os.close(self.stderr)

        if errstat.st_size:
            # errors have been written
            self.mailErrors()
            self.compress(self.thiserr)
            os.remove(self.thiserr)

        if outstat.st_size:
            self.compress(self.thislog)
            os.remove(self.thislog)

        if self.cache and self.cache():
            del self.cache()[self.repo]

    def mailErrors(self):
        # FIXME: this needs to be implemented for automation
        pass

class LogCache(dict):
    def __init__(self, ctx):
        self.ctx = ctx

    def __getitem__(self, name):
        if not self.has_key(name):
            self.__setitem__(name, Log(self.ctx, name, self))
        return dict.__getitem__(self, name)
