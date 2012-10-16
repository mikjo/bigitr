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

import setproctitle
import sys

class Proctitle(object):
    def __init__(self):
        self.oldtitle = setproctitle.getproctitle()

    def __call__(self, msg):
        setproctitle.setproctitle('bigitrd ' + msg)

    def __del__(self):
        setproctitle.setproctitle(self.oldtitle)


class Progress(object):
    def __init__(self, outFile=sys.stdout):
        self.outFile = outFile
        self.title = Proctitle()
        self.phase = ''
        self.contexts = set()
        self.msglen = 0

    def add(self, context):
        self.contexts.add(context)

    def remove(self, context):
        self.contexts.remove(context)

    def clear(self):
        self.contexts.clear()

    def setPhase(self, phaseName):
        self.phase = phaseName

    def report(self):
        msg = '%s: %s' %(self.phase, ' '.join(sorted(self.contexts)))
        self.title(msg)
        if self.outFile:
            self.outFile.write('\r' + ' '*self.msglen + '\r' + msg + '\r')
            self.outFile.flush()
        self.msglen = len(msg)

    def __del__(self):
        self.title('idle')
        if self.outFile:
            self.outFile.write('\r' + ' '*self.msglen + '\r')
            self.outFile.flush()
