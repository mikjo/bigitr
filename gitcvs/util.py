import os

def listFiles(path):
    allfiles = []
    dirlen = len(path) + 1
    for root, dirs, files in os.walk(path):
        allfiles.extend(['/'.join((root, x))[dirlen:] for x in files])
    return allfiles

def copyFiles(sourceDir, baseDir, fileNames):
    for fileName in fileNames:
        sourceFile = '/'.join((sourceDir, fileName))
        targetFile = '/'.join((baseDir, fileName))
        targetDir = os.path.dirname(targetFile)
        if not os.path.exists(targetDir):
            os.makedirs(targetDir)
        file(targetFile, 'w').write(file(sourceFile).read())

def copyTree(source, target):
    for dirpath, dirnames, filenames in os.walk(source):
        targetDir = '/'.join((target, dirpath[len(source):]))
        if not os.path.exists(targetDir):
            os.makedirs(targetDir)
        for filename in filenames:
            sourcePath = '/'.join((dirpath, filename))
            targetPath = '/'.join((targetDir, filename))
            file(targetPath, 'w').write(file(sourcePath).read())
            os.chmod(targetPath, os.stat(sourcePath).st_mode)

def removeRecursive(dir):
    for b, dirs, files in os.walk(dir, topdown=False):
        for f in files:
            os.remove('/'.join((b, f)))
        for d in dirs:
            os.rmdir('/'.join((b, d)))
    os.removedirs(dir)
