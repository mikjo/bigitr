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

import logging
import os
import subprocess
import time

class ErrorExitCode(ValueError):
    def __init__(self, retcode, *args, **kwargs):
        self.retcode = retcode
        ValueError.__init__(self, 'Unexpected exit code %d' %retcode,
            *args, **kwargs)

class LoggingShell(subprocess.Popen):
    def __init__(self, log, *args, **kwargs):
        self.log = log
        self.error = kwargs.pop('error', True)
        kwargs.setdefault('stderr', log.stderr)
        kwargs.setdefault('stdout', log.stdout)
        ts = self.timestamp()
        cmd = ' '.join(args)
        start = ' '.join((ts, 'START:', cmd, '\n'))
        os.write(log.stderr, start)
        os.write(log.stdout, start)
        self.log.markStart()
        self.p = subprocess.Popen.__init__(self, args, **kwargs)

    def _tzname(self):
        return time.tzname[time.daylight]

    def _now(self):
        return time.time()

    def timestamp(self):
        now = self._now()
        frac = '%4.4f' %(now - int(now))
        tzname = self._tzname()
        return time.strftime('[%a %b %d %H:%M:%S.'
                             + frac[2:] + ' ' + tzname + ' %Y]',
                             time.localtime(now))

    def finish(self):
        retcode = subprocess.Popen.wait(self)
        self.log.markStop()
        ts = self.timestamp()
        finish = '%s COMPLETE with return code: %d\n' %(ts, retcode)
        os.write(self.log.stderr, finish)
        os.write(self.log.stdout, finish)
        if retcode and self.error:
            for line in self.log.lastError().split('\n'):
                logging.error(line)
            logging.error(self.log.thiserr)
            raise ErrorExitCode(retcode)
        return retcode

def run(log, *args, **kwargs):
    s = LoggingShell(log, *args, **kwargs)
    return s.finish()

def read(log, *args, **kwargs):
    kwargs['stdout'] = subprocess.PIPE
    s = LoggingShell(log, *args, **kwargs)
    output = s.communicate()
    retcode = s.finish()
    return retcode, output[0]
