import os

def copyFiles(sourceDir, baseDir, fileNames):
    for fileName in fileNames:
        sourceFile = '/'.join((sourceDir, fileName))
        targetFile = '/'.join((baseDir, fileName))
        targetDir = os.path.dirname(targetFile)
        if not os.path.exists(targetDir):
            os.makedirs(targetDir)
        file(targetFile, 'w').write(file(sourceFile).read())
