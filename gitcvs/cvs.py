import os
import shell
import tempfile

# One CVS checkout per branch, because CVS switches branches slowly/poorly,
# so there is one CVS object per branch, not per repository.
# No checkout directory is created for exporting

def setCVSROOT(fn):
    def wrapper(self, *args, **kwargs):
        self.setEnvironment()
        fn(self, *args, **kwargs)
    return wrapper

def inCVSROOT(fn):
    def wrapper(self, *args, **kwargs):
        oldDir = os.getcwd()
        os.chdir(self.path)
        try:
            fn(self, *args, **kwargs)
        finally:
            os.chdir(oldDir)
    return wrapper

class CVS(object):
    def __init__(self, ctx, repo, branch, username):
        self.ctx = ctx
        self.location = self.ctx.getCVSPath(repo)
        self.path = ctx.getCVSBranchCheckoutDir(repo, branch)
        self.branch = branch
        self.log = self.ctx.logs[repo]
        self.root = ctx.getCVSRoot(repo, username)

    def setEnvironment(self):
        os.environ['CVSROOT'] = self.root

    def listContentFiles(self):
        allfiles = []
        dirlen = len(self.path) + 1
        for root, dirs, files in os.walk(self.path):
            if 'CVS' in dirs:
                dirs.remove('CVS') 
            allfiles.extend(['/'.join((root, x))[dirlen:] for x in files])
        return allfiles

    @setCVSROOT
    def export(self, targetDir):
        shell.run(self.log,
            'cvs', 'export', '-d', targetDir, '-r', self.branch, self.location)

    @setCVSROOT
    def checkout(self):
        shell.run(self.log,
            'cvs', 'checkout', '-d', self.path, '-r', self.branch, self.location)

    @inCVSROOT
    def update(self):
        shell.run(self.log, 'cvs', 'update', '-d')

    @inCVSROOT
    def deleteFiles(self, fileNames):
        shell.run(self.log, 'cvs', 'remove', *fileNames)

    def copyFiles(self, sourceDir, fileNames):
        'call addFiles for any files being added rather than updated'
        for fileName in fileNames:
            sourceFile = '/'.join((sourceDir, fileName))
            targetFile = '/'.join((self.path, fileName))
            targetDir = os.path.dirname(targetFile)
            if not os.path.exists(targetDir):
                os.makedirs(targetDir)
            file(targetFile, 'w').write(file(sourceFile).read())

    @inCVSROOT
    def addFiles(self, fileNames):
        shell.run(self.log, 'cvs', 'add', *fileNames)

    @inCVSROOT
    def commit(self, message):
        fd, name = tempfile.mkstemp('.gitcvs')
        os.write(fd, message)
        try:
            shell.run(self.log, 'cvs', 'commit', '-R', '-F', name)
        finally:
            os.remove(name)
            os.close(fd)
