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
import re

class Ignore(object):
    def __init__(self, log, specPath, regex=False):
        self.log = log
        self.patterns = None
        self.fileName = os.path.basename(specPath)
        self.regex = regex
        self.parse(specPath)

    def parse(self, specPath):
        if os.path.exists(specPath):
            self.patterns = [
                x.strip()
                for x in file(specPath).readlines()
                if not x.startswith('#')
            ]
        if self.regex and self.patterns:
            self.patterns = [(x, re.compile(x)) for x in self.patterns]

    def match(self, context, exp, pathSet):
        'Returns paths matching filters to exclude or include'
        if isinstance(exp, tuple):
            regex = exp[1]
            exp = exp[0]
            filtered = set(x for x in pathSet if regex.match(x))
        elif '/' in exp:
            filtered = set(fnmatch.filter(pathSet, exp))
        else:
            filtered = set()
            for path in pathSet:
                if fnmatch.fnmatch(os.path.basename(path), exp):
                    filtered.add(path)
        if filtered:
            for path in filtered:
                os.write(self.log.stderr,
                    '%s: %s %s file %s\n' %(self.fileName, exp, context, path))
        return filtered

    def filter(self, pathSet):
        'Returns paths not ignored'
        if self.patterns is None:
            return pathSet

        filtered = set(pathSet)

        for exp in self.patterns:
            ignored = self.match('ignores', exp, pathSet)
            filtered -= ignored

        return filtered

    def include(self, pathSet):
        'Returns paths explicitly included'
        # For files that positively include rather than negatively exclude
        if self.patterns is None:
            # if nothing is specified, everything is included
            return pathSet

        included = set()

        for exp in self.patterns:
            included.update(self.match('includes', exp, pathSet))

        return included
