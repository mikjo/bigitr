#
# Copyright 2014 SAS Institute
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

import fnmatch
import os

class Ignore(object):
    def __init__(self, log, ignorePath):
        self.log = log
        self.ignores = None
        self.fileName = os.path.basename(ignorePath)
        self.parse(ignorePath)

    def parse(self, ignorePath):
        if os.path.exists(ignorePath):
            self.ignores = [
                x.strip()
                for x in file(ignorePath).readlines()
                if not x.startswith('#')
            ]

    def match(self, exp, pathSet):
        'Returns paths to be filtered out'
        # ignored files will be the exception, no excessive optimization
        if '/' in exp:
            filtered = set(fnmatch.filter(pathSet, exp))
        else:
            filtered = set()
            for path in pathSet:
                if fnmatch.fnmatch(os.path.basename(path), exp):
                    filtered.add(path)
        if filtered:
            for path in filtered:
                os.write(self.log.stderr,
                    '%s: %s ignores file %s\n' %(self.fileName, exp, path))
        return filtered

    def filter(self, pathSet):
        'Returns paths not ignored'
        if self.ignores is None:
            return pathSet

        filtered = set(pathSet)

        for exp in self.ignores:
            ignored = self.match(exp, pathSet)
            filtered -= ignored

        return filtered
